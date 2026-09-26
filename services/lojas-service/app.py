from flask import Flask, jsonify, request, render_template

import db
import servicos

app = Flask(__name__)

db.init_schema([
    """CREATE TABLE IF NOT EXISTS lojas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(120) NOT NULL,
        descricao VARCHAR(255),
        endereco VARCHAR(255),
        contato VARCHAR(120),
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS produtos_lojas (
        loja_id INT NOT NULL,
        produto_id INT NOT NULL,
        estoque INT NOT NULL DEFAULT 0,
        PRIMARY KEY (loja_id, produto_id),
        CONSTRAINT fk_produtos_lojas_loja FOREIGN KEY (loja_id) REFERENCES lojas (id) ON DELETE CASCADE
    )""",
])

CAMPOS = ('nome', 'descricao', 'endereco', 'contato')


def payload():
    """Aceita JSON ou formulário."""
    return request.get_json(silent=True) or request.form.to_dict()


def buscar(loja_id):
    return db.query_one("SELECT * FROM lojas WHERE id = %s", (loja_id,))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/lojas', methods=['GET', 'POST'])
def lojas_route():
    if request.method == 'POST':
        data = payload()
        if not (data.get('nome') or '').strip():
            return jsonify({"message": "Informe o nome da loja"}), 400
        loja_id, _ = db.execute(
            "INSERT INTO lojas (nome, descricao, endereco, contato) VALUES (%s, %s, %s, %s)",
            tuple((data.get(c) or '').strip() for c in CAMPOS),
        )
        return jsonify({"message": "Loja cadastrada com sucesso", "loja_id": loja_id, "loja": buscar(loja_id)}), 201
    return jsonify({"lojas": db.query("SELECT * FROM lojas ORDER BY id")})


@app.route('/lojas/<int:loja_id>', methods=['GET', 'PUT', 'DELETE'])
def loja_route(loja_id):
    loja = buscar(loja_id)
    if not loja:
        return jsonify({"message": f"Loja {loja_id} não encontrada"}), 404
    if request.method == 'GET':
        return jsonify({"loja": loja})
    if request.method == 'PUT':
        data = payload()
        valores = tuple((data.get(c) if c in data else loja[c]) for c in CAMPOS)
        db.execute("UPDATE lojas SET nome = %s, descricao = %s, endereco = %s, contato = %s WHERE id = %s",
                   valores + (loja_id,))
        return jsonify({"message": "Loja atualizada com sucesso", "loja": buscar(loja_id)})
    db.execute("DELETE FROM lojas WHERE id = %s", (loja_id,))
    return jsonify({"message": "Loja removida com sucesso"})


@app.route('/produtos_lojas', methods=['POST'])
def produtos_lojas_route():
    data = payload()
    try:
        loja_id = int(data.get('loja_id'))
        produto_id = int(data.get('produto_id'))
        estoque = int(data.get('estoque') or 0)
    except (TypeError, ValueError):
        return jsonify({"message": "loja_id, produto_id e estoque devem ser números"}), 400
    if estoque < 0:
        return jsonify({"message": "Estoque não pode ser negativo"}), 400
    if not buscar(loja_id):
        return jsonify({"message": f"Loja {loja_id} não encontrada"}), 404
    try:
        code, _ = servicos.chamar('GET', servicos.url('items', f'/itens/{produto_id}'))
    except servicos.Indisponivel:
        return jsonify({"message": "items-service indisponível"}), 503
    if code == 404:
        return jsonify({"message": f"Produto {produto_id} não existe no items-service"}), 404
    db.execute(
        "INSERT INTO produtos_lojas (loja_id, produto_id, estoque) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE estoque = VALUES(estoque)",
        (loja_id, produto_id, estoque),
    )
    return jsonify({
        "message": f"Produto {produto_id} associado à loja {loja_id} com sucesso",
        "produtos_lojas": db.query("SELECT * FROM produtos_lojas WHERE loja_id = %s ORDER BY produto_id", (loja_id,)),
    }), 201


@app.route('/dashboard/<int:loja_id>')
def dashboard(loja_id):
    loja = buscar(loja_id)
    if not loja:
        return jsonify({"message": f"Loja {loja_id} não encontrada"}), 404
    estoque = db.query("SELECT produto_id, estoque FROM produtos_lojas WHERE loja_id = %s ORDER BY produto_id", (loja_id,))
    avisos = []
    try:
        _, body = servicos.chamar('GET', servicos.url('items', '/itens'))
        catalogo = {i['id']: i for i in body['itens']}
        for linha in estoque:
            item = catalogo.get(linha['produto_id'], {})
            linha['nome'], linha['preco'] = item.get('nome'), item.get('preco')
    except servicos.Indisponivel:
        avisos.append("items-service indisponível: estoque sem nome e preço")
    try:
        _, vendas = servicos.chamar('GET', servicos.url('pedidos', f'/pedidos?loja_id={loja_id}'))
    except servicos.Indisponivel:
        vendas = []
        avisos.append("pedidos-service indisponível: vendas não carregadas")
    faturamento = round(sum(v['total'] or 0 for v in vendas if v['status'] in ('pago', 'enviado', 'entregue')), 2)
    return jsonify({"loja": loja, "vendas": vendas, "estoque": estoque, "faturamento": faturamento, "avisos": avisos})


@app.route('/historico')
def historico():
    return jsonify({
        "total_lojas": db.query_one("SELECT COUNT(*) AS n FROM lojas")["n"],
        "total_produtos_associados": db.query_one("SELECT COUNT(*) AS n FROM produtos_lojas")["n"],
    })


@app.route('/status')
def status():
    ok = db.healthy()
    return jsonify({"status": "ok" if ok else "degradado", "database": "ok" if ok else "indisponível"}), 200 if ok else 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8282)
