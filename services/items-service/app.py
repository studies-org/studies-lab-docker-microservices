from flask import Flask, jsonify, request

import db

app = Flask(__name__)

db.init_schema([
    """CREATE TABLE IF NOT EXISTS itens (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(120) NOT NULL,
        descricao VARCHAR(255),
        preco DECIMAL(10, 2) NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
])


def payload():
    """Aceita JSON ou formulário."""
    return request.get_json(silent=True) or request.form.to_dict()


def parse_preco(valor):
    try:
        preco = round(float(valor), 2)
    except (TypeError, ValueError):
        return None
    return preco if preco >= 0 else None


def buscar(item_id):
    return db.query_one("SELECT * FROM itens WHERE id = %s", (item_id,))


@app.route('/favicon.ico')
def favicon():
    return '', 204


ROTAS = [
    "GET /itens",
    "POST /itens",
    "GET /itens/<id>",
    "PUT /itens/<id>",
    "DELETE /itens/<id>",
    "GET /status",
]


@app.route('/')
def home():
    return jsonify({"servico": "items-service", "rotas": ROTAS})


@app.route('/itens', methods=['GET', 'POST'])
def itens_route():
    if request.method == 'POST':
        data = payload()
        nome = (data.get('nome') or '').strip()
        preco = parse_preco(data.get('preco'))
        if not nome or preco is None:
            return jsonify({"message": "Informe nome e um preço válido (>= 0)"}), 400
        item_id, _ = db.execute(
            "INSERT INTO itens (nome, descricao, preco) VALUES (%s, %s, %s)",
            (nome, data.get('descricao'), preco),
        )
        return jsonify({"message": "Item cadastrado com sucesso", "item": buscar(item_id)}), 201
    return jsonify({"itens": db.query("SELECT * FROM itens ORDER BY id")})


@app.route('/itens/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
def item_route(item_id):
    item = buscar(item_id)
    if not item:
        return jsonify({"message": "Item não encontrado"}), 404

    if request.method == 'GET':
        return jsonify({"item": item})

    if request.method == 'PUT':
        data = payload()
        nome = (data.get('nome') or item["nome"]).strip()
        preco = parse_preco(data['preco']) if 'preco' in data else item["preco"]
        if preco is None:
            return jsonify({"message": "Preço inválido"}), 400
        db.execute(
            "UPDATE itens SET nome = %s, descricao = %s, preco = %s WHERE id = %s",
            (nome, data.get('descricao', item["descricao"]), preco, item_id),
        )
        return jsonify({"message": "Item atualizado com sucesso", "item": buscar(item_id)})

    db.execute("DELETE FROM itens WHERE id = %s", (item_id,))
    return jsonify({"message": "Item removido com sucesso"})


@app.route('/status')
def status():
    ok = db.healthy()
    return jsonify({"status": "ok" if ok else "degradado", "database": "ok" if ok else "indisponível"}), 200 if ok else 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8383)
