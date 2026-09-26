import json
import uuid

from flask import Flask, jsonify, render_template, request

import db

app = Flask(__name__)

FORMAS_PADRAO = ["cartao_credito", "boleto", "pix"]

db.init_schema([
    """CREATE TABLE IF NOT EXISTS formas_pagamento (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(40) NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS transacoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tipo VARCHAR(40) NOT NULL,
        pedido_id INT NULL,
        valor DECIMAL(10, 2) NULL,
        detalhes JSON NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "INSERT IGNORE INTO formas_pagamento (nome) VALUES " + ", ".join(f"('{f}')" for f in FORMAS_PADRAO),
])


def payload():
    """Aceita JSON ou formulário."""
    return request.get_json(silent=True) or request.form.to_dict()


def simular(tipo, referencia):
    """Integração fictícia com o gateway: nada sai do container."""
    codigo = uuid.uuid4().hex[:12]
    if tipo == "cartao_credito":
        final = ''.join(ch for ch in str(referencia) if ch.isdigit())[-4:] or "0000"
        return {"id": f"ch_{codigo}", "status": "succeeded", "cartao": f"**** **** **** {final}"}
    if tipo == "boleto":
        return {"id": f"bol_{codigo}", "status": "pending", "linha_digitavel": f"99999.{codigo[:5]} {codigo[5:10]}.000000 0 {codigo[10:]}00"}
    return {"id": f"pix_{codigo}", "status": "succeeded", "copia_e_cola": f"00020126360014BR.GOV.BCB.PIX0114lab{codigo}"}


def registrar(tipo, detalhes, pedido_id=None, valor=None):
    transacao_id, _ = db.execute(
        "INSERT INTO transacoes (tipo, pedido_id, valor, detalhes) VALUES (%s, %s, %s, %s)",
        (tipo, pedido_id, valor, json.dumps(detalhes)),
    )
    return transacao_id


def listar_transacoes():
    rows = db.query("SELECT * FROM transacoes ORDER BY id DESC")
    for row in rows:
        row["detalhes"] = json.loads(row["detalhes"])
    return rows


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        data = payload()
        for campo, tipo in (("cartao", "cartao_credito"), ("boleto", "boleto"), ("pix", "pix")):
            if data.get(campo):
                detalhes = simular(tipo, data[campo])
                registrar(tipo, detalhes)
                return jsonify({"data": {tipo: detalhes}})
        return jsonify({"message": "Informe cartao, boleto ou pix"}), 400
    return render_template('index.html')


@app.route('/status')
def status():
    ok = db.healthy()
    return jsonify({"status": "ok" if ok else "degradado", "database": "ok" if ok else "indisponível"}), 200 if ok else 503


@app.route('/formas_pagamento', methods=['GET', 'POST'])
def formas_pagamento_route():
    if request.method == 'POST':
        nova_forma = (payload().get('forma_pagamento') or '').strip()
        if not nova_forma:
            return jsonify({"message": "Informe a forma de pagamento"}), 400
        db.execute("INSERT IGNORE INTO formas_pagamento (nome) VALUES (%s)", (nova_forma,))
        status_code = 201
    else:
        status_code = 200
    formas = [r["nome"] for r in db.query("SELECT nome FROM formas_pagamento ORDER BY id")]
    resposta = {"formas_pagamento": formas}
    if request.method == 'POST':
        resposta["message"] = "Forma de pagamento cadastrada com sucesso"
    return jsonify(resposta), status_code


@app.route('/historico')
def historico():
    return jsonify({"historico": listar_transacoes()})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8181)
