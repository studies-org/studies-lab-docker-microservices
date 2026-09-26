"""Teste de ponta a ponta do lab, passando pelo painel (nginx) em todas as rotas.

Uso: python3 scripts/smoke_test.py [http://localhost:8000]
Precisa da stack no ar (docker compose up -d --wait). Cria dados novos a cada execução.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
falhas = []
total = 0


def call(metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(BASE + caminho, data=dados, method=metodo, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw and resp.headers.get_content_type() == "application/json" else raw)
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, raw


def check(nome, ok):
    global total
    total += 1
    print(("  ok   " if ok else "  FALHA ") + nome)
    if not ok:
        falhas.append(nome)


def main():
    print(f"Smoke test em {BASE}")

    code, body = call("GET", "/healthz")
    check("painel responde /healthz", code == 200)
    code, body = call("GET", "/")
    check("painel serve a UI", code == 200 and b"Balc" in body)
    for svc in ("items", "lojas", "pedidos", "pagamentos"):
        code, body = call("GET", f"/api/{svc}/status")
        check(f"{svc}-service online com banco", code == 200 and body.get("database") == "ok")
        code, body = call("GET", f"/api/{svc}/")
        check(f"{svc}-service lista as rotas em /", code == 200 and body["rotas"])

    # items-service
    code, body = call("POST", "/api/items/itens", {"nome": "Teclado", "descricao": "ABNT2", "preco": 100})
    check("POST /itens cria item", code == 201)
    item_a = body["item"]["id"]
    code, body = call("POST", "/api/items/itens", {"nome": "Mouse", "preco": 50.5})
    item_b = body["item"]["id"]
    check("POST /itens sem preço devolve 400", call("POST", "/api/items/itens", {"nome": "x"})[0] == 400)
    code, body = call("PUT", f"/api/items/itens/{item_b}", {"preco": 40})
    check("PUT /itens/<id> atualiza preço", code == 200 and body["item"]["preco"] == 40)
    code, body = call("GET", f"/api/items/itens/{item_a}")
    check("GET /itens/<id>", code == 200 and body["item"]["nome"] == "Teclado")
    code, body = call("GET", "/api/items/itens")
    check("GET /itens lista", code == 200 and any(i["id"] == item_a for i in body["itens"]))
    code, body = call("POST", "/api/items/itens", {"nome": "Temporário", "preco": 1})
    tmp = body["item"]["id"]
    check("DELETE /itens/<id>", call("DELETE", f"/api/items/itens/{tmp}")[0] == 200)
    check("GET item removido devolve 404", call("GET", f"/api/items/itens/{tmp}")[0] == 404)

    # lojas-service
    code, body = call("POST", "/api/lojas/lojas", {"nome": "Loja Teste", "endereco": "Rua 1", "contato": "11"})
    check("POST /lojas cria loja", code == 201)
    loja = body["loja_id"]
    check("GET /lojas lista", any(x["id"] == loja for x in call("GET", "/api/lojas/lojas")[1]["lojas"]))
    code, body = call("PUT", f"/api/lojas/lojas/{loja}", {"contato": "(11) 4000-0000"})
    check("PUT /lojas/<id>", code == 200 and body["loja"]["contato"] == "(11) 4000-0000")
    check("GET /lojas/<id>", call("GET", f"/api/lojas/lojas/{loja}")[0] == 200)
    code, _ = call("POST", "/api/lojas/produtos_lojas", {"loja_id": loja, "produto_id": item_a, "estoque": 7})
    check("POST /produtos_lojas associa item com estoque", code == 201)
    code, _ = call("POST", "/api/lojas/produtos_lojas", {"loja_id": loja, "produto_id": 999999})
    check("POST /produtos_lojas com item inexistente devolve 404 (consulta o items-service)", code == 404)
    code, body = call("GET", "/api/lojas/historico")
    check("GET /historico das lojas", code == 200 and body["total_lojas"] >= 1)

    # pedidos-service
    pedido = {"cliente_id": 900, "loja_id": loja, "forma_pagamento": "pix",
              "itens": [{"produto_id": item_a, "quantidade": 2}, {"produto_id": item_b, "quantidade": 1}]}
    code, body = call("POST", "/api/pedidos/pedidos", pedido)
    check("POST /pedidos cria pedido", code == 201)
    check("total vem do items-service (2 x 100 + 40)", body.get("total") == 240)
    p1 = body["id"]
    code, _ = call("POST", "/api/pedidos/pedidos", {**pedido, "itens": [{"produto_id": 999999, "quantidade": 1}]})
    check("pedido com item inexistente devolve 422", code == 422)
    code, _ = call("POST", "/api/pedidos/pedidos", {**pedido, "loja_id": 999999})
    check("pedido com loja inexistente devolve 422", code == 422)
    check("pedido sem itens devolve 400", call("POST", "/api/pedidos/pedidos", {"cliente_id": 1})[0] == 400)
    code, body = call("POST", "/api/pedidos/pedidos", {**pedido, "forma_pagamento": "boleto"})
    p2 = body["id"]
    code, body = call("POST", "/api/pedidos/pedidos", {**pedido, "forma_pagamento": "cartao_credito"})
    p3 = body["id"]
    code, body = call("GET", f"/api/pedidos/pedidos/{p1}")
    check("GET /pedidos/<id>", code == 200 and body["status"] == "em processamento")
    check("GET /pedidos?loja_id=", len(call("GET", f"/api/pedidos/pedidos?loja_id={loja}")[1]) == 3)
    check("GET /clientes/<id>/pedidos", len(call("GET", "/api/pedidos/clientes/900/pedidos")[1]) >= 3)
    check("status inválido devolve 400", call("PUT", f"/api/pedidos/pedidos/{p3}/status", {"status": "voando"})[0] == 400)

    # pagamentos-service
    code, body = call("GET", "/api/pagamentos/formas_pagamento")
    check("GET /formas_pagamento traz as 3 padrão", {"cartao_credito", "boleto", "pix"} <= set(body["formas_pagamento"]))
    code, body = call("POST", "/api/pagamentos/formas_pagamento", {"forma_pagamento": "vale"})
    check("POST /formas_pagamento cadastra", code == 201 and "vale" in body["formas_pagamento"])
    code, body = call("POST", "/api/pagamentos/pagamentos", {"pedido_id": p1, "forma_pagamento": "pix"})
    check("PIX aprova na hora", code == 201 and body["transacao"]["detalhes"]["status"] == "succeeded")
    check("valor do pagamento vem do pedido", body["transacao"]["valor"] == 240)
    check("pedido pago vira 'pago'", call("GET", f"/api/pedidos/pedidos/{p1}")[1]["status"] == "pago")
    check("pagar de novo devolve 409", call("POST", "/api/pagamentos/pagamentos", {"pedido_id": p1, "forma_pagamento": "pix"})[0] == 409)
    code, body = call("POST", "/api/pagamentos/pagamentos", {"pedido_id": p3, "forma_pagamento": "cartao_credito", "cartao": "4111 1111 1111 1234"})
    check("cartão mascarado", code == 201 and body["transacao"]["detalhes"]["cartao"].endswith("1234") and "4111" not in json.dumps(body))
    code, body = call("POST", "/api/pagamentos/pagamentos", {"pedido_id": p2, "forma_pagamento": "boleto"})
    boleto = body["transacao"]["id"]
    check("boleto fica pendente", code == 201 and body["transacao"]["detalhes"]["status"] == "pending")
    check("pedido do boleto continua em processamento", call("GET", f"/api/pedidos/pedidos/{p2}")[1]["status"] == "em processamento")
    check("GET /pagamentos/<id>", call("GET", f"/api/pagamentos/pagamentos/{boleto}")[0] == 200)
    check("POST /pagamentos/<id>/confirmar", call("POST", f"/api/pagamentos/pagamentos/{boleto}/confirmar")[0] == 200)
    check("boleto confirmado deixa o pedido pago", call("GET", f"/api/pedidos/pedidos/{p2}")[1]["status"] == "pago")
    check("forma sem integração devolve 422", call("POST", "/api/pagamentos/pagamentos", {"pedido_id": p3, "forma_pagamento": "vale"})[0] == 422)
    check("pedido inexistente devolve 404", call("POST", "/api/pagamentos/pagamentos", {"pedido_id": 999999, "forma_pagamento": "pix"})[0] == 404)
    code, body = call("GET", "/api/pagamentos/historico")
    check("GET /historico de transações", code == 200 and len(body["historico"]) >= 3)

    # Fluxo completo refletido no dashboard da loja
    check("PUT /pedidos/<id>/status enviado", call("PUT", f"/api/pedidos/pedidos/{p1}/status", {"status": "enviado"})[0] == 200)
    code, body = call("GET", f"/api/lojas/dashboard/{loja}")
    check("dashboard traz estoque com nome e preço", code == 200 and body["estoque"][0]["nome"] == "Teclado")
    check("dashboard soma o faturamento dos 3 pedidos pagos", body["faturamento"] == 720 and len(body["vendas"]) == 3)
    check("DELETE /lojas/<id>", call("DELETE", f"/api/lojas/lojas/{loja}")[0] == 200)

    print(f"\n{total - len(falhas)}/{total} verificações passaram")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
