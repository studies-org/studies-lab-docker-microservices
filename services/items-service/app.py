from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Simulação de banco de dados em memória
itens = []

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/itens', methods=['GET', 'POST'])
def itens_route():
    if request.method == 'POST':
        novo_item = {
            "id": len(itens) + 1,
            "nome": request.form.get('nome'),
            "descricao": request.form.get('descricao'),
            "preco": float(request.form.get('preco'))
        }
        itens.append(novo_item)
        return jsonify({"message": "Item cadastrado com sucesso", "item": novo_item})
    return jsonify({"itens": itens})

@app.route('/itens/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
def item_route(item_id):
    item = next((item for item in itens if item["id"] == item_id), None)
    if not item:
        return jsonify({"message": "Item não encontrado"}), 404

    if request.method == 'GET':
        return jsonify({"item": item})

    if request.method == 'PUT':
        item["nome"] = request.form.get('nome', item["nome"])
        item["descricao"] = request.form.get('descricao', item["descricao"])
        item["preco"] = float(request.form.get('preco', item["preco"]))
        return jsonify({"message": "Item atualizado com sucesso", "item": item})

    if request.method == 'DELETE':
        itens.remove(item)
        return jsonify({"message": "Item removido com sucesso"})

@app.route('/status')
def status():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8383)