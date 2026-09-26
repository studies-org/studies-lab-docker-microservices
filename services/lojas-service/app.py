from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Simulação de banco de dados em memória
lojas = []
produtos_lojas = []
historico_vendas = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/lojas', methods=['GET', 'POST'])
def lojas_route():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        endereco = request.form.get('endereco')
        contato = request.form.get('contato')
        loja_id = len(lojas) + 1
        loja = {"id": loja_id, "nome": nome, "descricao": descricao, "endereco": endereco, "contato": contato}
        lojas.append(loja)
        return jsonify({"message": "Loja cadastrada com sucesso", "loja_id": loja_id, "lojas": lojas})
    return jsonify({"lojas": lojas})

@app.route('/produtos_lojas', methods=['POST'])
def produtos_lojas_route():
    loja_id = request.form.get('loja_id')
    produto_id = request.form.get('produto_id')
    produto_loja = {"loja_id": loja_id, "produto_id": produto_id}
    produtos_lojas.append(produto_loja)
    return jsonify({"message": f"Produto {produto_id} associado à loja {loja_id} com sucesso", "produtos_lojas": produtos_lojas})

@app.route('/dashboard/<int:loja_id>')
def dashboard(loja_id):
    vendas = [venda for venda in historico_vendas if venda.get('loja_id') == loja_id]
    estoque = [produto for produto in produtos_lojas if produto.get('loja_id') == loja_id]
    return jsonify({"vendas": vendas, "estoque": estoque})


@app.route('/status')
def status():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8282)
