"""Popula o lab com itens, lojas, pedidos e pagamentos de exemplo, pelo painel.

Uso: python3 scripts/seed.py [http://localhost:8000]
"""
import json
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def call(metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(BASE + caminho, data=dados, method=metodo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


ITENS = [
    ("Teclado mecânico", "ABNT2, switch marrom", 349.90),
    ("Mouse sem fio", "1600 dpi, silencioso", 129.90),
    ("Monitor 27\"", "QHD, 75 Hz", 1499.00),
    ("Headset", "Microfone com cancelamento de ruído", 279.50),
    ("Webcam Full HD", "1080p, foco automático", 219.00),
    ("Hub USB-C", "7 portas, HDMI 4K", 189.90),
]
LOJAS = [
    ("Loja Centro", "Rua das Flores, 120", "(11) 4000-1001"),
    ("Loja Shopping Norte", "Av. Brasil, 2500, piso 2", "(11) 4000-1002"),
]


def main():
    itens = [call("POST", "/api/items/itens", {"nome": n, "descricao": d, "preco": p})["item"]["id"] for n, d, p in ITENS]
    lojas = [call("POST", "/api/lojas/lojas", {"nome": n, "endereco": e, "contato": c})["loja_id"] for n, e, c in LOJAS]
    for loja, estoques in zip(lojas, [(12, 30, 5, 8, 0, 15), (6, 20, 3, 10, 9, 0)]):
        for item, qtd in zip(itens, estoques):
            if qtd:
                call("POST", "/api/lojas/produtos_lojas", {"loja_id": loja, "produto_id": item, "estoque": qtd})

    pedidos = [
        (101, lojas[0], [(itens[0], 1), (itens[1], 1)], "pix"),
        (102, lojas[0], [(itens[2], 2)], "cartao_credito"),
        (103, lojas[1], [(itens[3], 1), (itens[5], 2)], "boleto"),
        (101, lojas[1], [(itens[4], 1)], "pix"),
        (104, lojas[0], [(itens[1], 3)], "cartao_credito"),
    ]
    ids = []
    for cliente, loja, linhas, forma in pedidos:
        corpo = {"cliente_id": cliente, "loja_id": loja, "forma_pagamento": forma,
                 "itens": [{"produto_id": i, "quantidade": q} for i, q in linhas]}
        ids.append((call("POST", "/api/pedidos/pedidos", corpo)["id"], forma))

    # Paga os três primeiros; o boleto fica pendente, o último fica em processamento
    for pedido_id, forma in ids[:3]:
        call("POST", "/api/pagamentos/pagamentos", {"pedido_id": pedido_id, "forma_pagamento": forma, "cartao": "4111111111111111"})
    call("PUT", f"/api/pedidos/pedidos/{ids[0][0]}/status", {"status": "enviado"})
    print(f"{len(itens)} itens, {len(lojas)} lojas, {len(ids)} pedidos e 3 pagamentos criados em {BASE}")


if __name__ == "__main__":
    main()
