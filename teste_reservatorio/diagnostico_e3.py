"""
diagnostico_e3.py
Envia o mesmo valor à tag 'Nivel' em cinco formatos diferentes, com uma pausa entre eles,
para descobrir se o E3 não mostra o valor por causa do FORMATO (por exemplo, separador decimal).
Observe a tag (ou o objeto de exibição) no E3 durante as pausas e anote quais valores aparecem.
"""
import time

import requests

from config import E3_URL, TIMEOUT_HTTP_S

ENTITY = "Nivel"
PAUSA_S = 6

VARIANTES = [
    ("texto com ponto   '55.3'", "55.3"),
    ("texto com vírgula '55,3'", "55,3"),
    ("texto inteiro     '56'", "56"),
    ("número JSON       57.3", 57.3),
    ("número JSON       58", 58),
]

for descricao, valor in VARIANTES:
    try:
        resp = requests.post(
            E3_URL,
            json={"Value": valor, "Quality": 192},
            headers={"Operation": "UPDATE TAG", "Entity": ENTITY},
            timeout=TIMEOUT_HTTP_S,
        )
        print(f"Enviado {descricao} -> HTTP {resp.status_code} {resp.text[:80]!r}")
    except requests.RequestException as erro:
        print(f"Enviado {descricao} -> FALHA: {erro}")
        break
    print(f"   observe a tag '{ENTITY}' no E3 durante {PAUSA_S} s...")
    time.sleep(PAUSA_S)

print("\nAnote quais valores apareceram na tag: 55.3, 5530, 55,3, 56, 57.3 ou 58.")