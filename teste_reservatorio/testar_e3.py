"""
testar_e3.py
Envia valores fixos ao driver SequenceWebService do E3, sem usar o CODESYS.
Resposta esperada para cada variável: {"Err":0,"ErrMsg":"OK"}
"""
from datetime import datetime

import requests

from config import E3_URL, TIMEOUT_HTTP_S

VALORES = {
    "Nivel": "55.3",
    "Temperatura": "25.1",
    "Vazao": "20.0",
    "BombaLigada": "1",
}

for entity, valor in VALORES.items():
    try:
        resp = requests.post(
            E3_URL,
            json={"Value": valor, "Quality": 192,
                  "Time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")},
            headers={"Operation": "UPDATE TAG", "Entity": entity},
            timeout=TIMEOUT_HTTP_S,
        )
        print(f"{entity}: HTTP {resp.status_code} -> {resp.text[:150]!r}")
    except requests.RequestException as erro:
        print(f"{entity}: FALHA -> {erro}")