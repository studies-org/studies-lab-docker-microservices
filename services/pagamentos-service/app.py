from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Simulação de banco de dados em memória
formas_pagamento = []
historico_transacoes = []

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        cartao_credito = request.form.get('cartao')
        boleto = request.form.get('boleto')
        pix = request.form.get('pix')
        
        # Exemplo de integração fictícia com Stripe
        if cartao_credito:
            charge = {
                "id": "ch_1Example",
                "amount": 1000,
                "currency": "brl",
                "description": "Pagamento com cartão de crédito",
                "status": "succeeded"
            }
            transacao = {"tipo": "cartao_credito", "detalhes": charge}
            historico_transacoes.append(transacao)
            return jsonify({"data": {"cartao_credito": charge}})
        
        # Exemplo de integração fictícia com PagSeguro para boleto
        if boleto:
            response = {
                "payment_url": "https://pagseguro.uol.com.br/checkout/payment/boleto/1234567890"
            }
            transacao = {"tipo": "boleto", "detalhes": response}
            historico_transacoes.append(transacao)
            return jsonify({"data": {"boleto": response}})
        
        # Exemplo de integração fictícia com PagSeguro para PIX
        if pix:
            response = {
                "payment_url": "https://pagseguro.uol.com.br/checkout/payment/pix/0987654321"
            }
            transacao = {"tipo": "pix", "detalhes": response}
            historico_transacoes.append(transacao)
            return jsonify({"data": {"pix": response}})
        
        return jsonify({"data": {"cartao_credito": cartao_credito, "boleto": boleto, "pix": pix}})
    return render_template('index.html')

@app.route('/status')
def status():
    return jsonify({"status": "ok"})

@app.route('/formas_pagamento', methods=['GET', 'POST'])
def formas_pagamento_route():
    if request.method == 'POST':
        nova_forma = request.form.get('forma_pagamento')
        formas_pagamento.append(nova_forma)
        return jsonify({"message": "Forma de pagamento cadastrada com sucesso", "formas_pagamento": formas_pagamento})
    return jsonify({"formas_pagamento": formas_pagamento})

@app.route('/historico')
def historico():
    return jsonify({"historico": historico_transacoes})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8181)