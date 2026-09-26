from flask import Flask, jsonify, request

import db
import servicos

app = Flask(__name__)

STATUS = ["em processamento", "pago", "enviado", "entregue", "cancelado"]

db.init_schema([
    """CREATE TABLE IF NOT EXISTS pedidos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cliente_id INT NOT NULL,
        loja_id INT NULL,
        forma_pagamento VARCHAR(40) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'em processamento',
        total DECIMAL(10, 2) NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_pedidos_cliente (cliente_id),
        INDEX idx_pedidos_loja (loja_id)
    )""",
    """CREATE TABLE IF NOT EXISTS pedido_itens (
        pedido_id INT NOT NULL,
        produto_id INT NOT NULL,
        quantidade INT NOT NULL,
        preco_unitario DECIMAL(10, 2) NULL,
        PRIMARY KEY (pedido_id, produto_id),
        CONSTRAINT fk_pedido_itens_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE
    )""",
])


def carregar(pedidos):
    """Anexa os itens de cada pedido."""
    for pedido in pedidos:
        pedido['itens'] = db.query(
            "SELECT produto_id, quantidade, preco_unitario FROM pedido_itens WHERE pedido_id = %s ORDER BY produto_id",
            (pedido['id'],),
        )
    return pedidos


def buscar(pedido_id):
    pedido = db.query_one("SELECT * FROM pedidos WHERE id = %s", (pedido_id,))
    return carregar([pedido])[0] if pedido else None


def ler_pedido(data):
    """Valida o corpo do POST /pedidos. Devolve (dados, erro)."""
    try:
        itens = {}
        for item in data['itens']:
            produto_id, quantidade = int(item['produto_id']), int(item['quantidade'])
            itens[produto_id] = itens.get(produto_id, 0) + quantidade
        cliente_id = int(data['cliente_id'])
        loja_id = int(data['loja_id']) if data.get('loja_id') not in (None, '') else None
        forma_pagamento = str(data['forma_pagamento']).strip()
    except (KeyError, TypeError, ValueError):
        return None, 'Envie cliente_id, forma_pagamento e itens [{produto_id, quantidade}]'
    if not itens or any(q <= 0 for q in itens.values()) or not forma_pagamento:
        return None, 'O pedido precisa de ao menos um item com quantidade positiva'
    return dict(cliente_id=cliente_id, loja_id=loja_id, forma_pagamento=forma_pagamento, itens=itens), None


ROTAS = [
    "GET /pedidos",
    "POST /pedidos",
    "GET /pedidos/<id>",
    "PUT /pedidos/<id>/status",
    "GET /clientes/<cliente_id>/pedidos",
    "GET /status",
]


@app.route('/')
def home():
    return jsonify({"servico": "pedidos-service", "rotas": ROTAS})


@app.route('/status')
def status():
    ok = db.healthy()
    return jsonify({"status": "ok" if ok else "degradado", "database": "ok" if ok else "indisponível"}), 200 if ok else 503


@app.route('/pedidos', methods=['GET', 'POST'])
def pedidos_route():
    if request.method == 'GET':
        if request.args.get('loja_id'):
            rows = db.query("SELECT * FROM pedidos WHERE loja_id = %s ORDER BY id DESC", (request.args.get('loja_id'),))
        else:
            rows = db.query("SELECT * FROM pedidos ORDER BY id DESC")
        return jsonify(carregar(rows))

    pedido, erro = ler_pedido(request.get_json(silent=True) or {})
    if erro:
        return jsonify({'error': erro}), 400

    # Preço sempre vem do items-service, nunca do cliente
    try:
        if pedido['loja_id'] is not None:
            code, _ = servicos.chamar('GET', servicos.url('lojas', f"/lojas/{pedido['loja_id']}"))
            if code == 404:
                return jsonify({'error': f"Loja {pedido['loja_id']} não encontrada"}), 422
        precos = {}
        for produto_id in pedido['itens']:
            code, body = servicos.chamar('GET', servicos.url('items', f'/itens/{produto_id}'))
            if code == 404:
                return jsonify({'error': f'Produto {produto_id} não encontrado no catálogo'}), 422
            precos[produto_id] = body['item']['preco']
    except servicos.Indisponivel as err:
        return jsonify({'error': f'Serviço indisponível: {err}'}), 503

    total = round(sum(precos[pid] * q for pid, q in pedido['itens'].items()), 2)
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO pedidos (cliente_id, loja_id, forma_pagamento, total) VALUES (%s, %s, %s, %s)",
            (pedido['cliente_id'], pedido['loja_id'], pedido['forma_pagamento'], total),
        )
        pedido_id = cur.lastrowid
        cur.executemany(
            "INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario) VALUES (%s, %s, %s, %s)",
            [(pedido_id, pid, q, precos[pid]) for pid, q in pedido['itens'].items()],
        )
    return jsonify(buscar(pedido_id)), 201


@app.route('/pedidos/<int:pedido_id>', methods=['GET'])
def status_pedido(pedido_id):
    pedido = buscar(pedido_id)
    if pedido:
        return jsonify(pedido)
    return jsonify({'error': 'Pedido não encontrado'}), 404


@app.route('/pedidos/<int:pedido_id>/status', methods=['PUT'])
def atualizar_status_pedido(pedido_id):
    novo_status = (request.get_json(silent=True) or {}).get('status')
    if novo_status not in STATUS:
        return jsonify({'error': 'Status inválido', 'validos': STATUS}), 400
    _, alterados = db.execute("UPDATE pedidos SET status = %s WHERE id = %s", (novo_status, pedido_id))
    if not alterados and not buscar(pedido_id):
        return jsonify({'error': 'Pedido não encontrado'}), 404
    return jsonify({'id': pedido_id, 'status': novo_status})


@app.route('/clientes/<int:cliente_id>/pedidos', methods=['GET'])
def historico_pedidos(cliente_id):
    return jsonify(carregar(db.query("SELECT * FROM pedidos WHERE cliente_id = %s ORDER BY id DESC", (cliente_id,))))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
