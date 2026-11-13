"""
testar_campo_ordem.py
Descobre qual campo da Work Order aceita texto livre via API (PATCH) na sua versão do OpenMES.
Só testa campos que já aparecem na leitura da ordem e restaura o valor original depois.
A ordem precisa estar em 'pending' ou 'accepted' para ser editável.
"""
import requests

import openmes_cliente as openmes
from config import OPENMES_URL, OPENMES_WORK_ORDER_ID, TIMEOUT_HTTP_S

CANDIDATOS = ["production_notes", "description", "notes", "product_name"]
TEXTO_TESTE = "Teste de integração CODESYS (será restaurado)"


def main():
    cab = {"Authorization": f"Bearer {openmes.obter_token()}", "Accept": "application/json"}
    url = f"{OPENMES_URL}/api/v1/work-orders/{OPENMES_WORK_ORDER_ID}"

    r = requests.get(url, headers=cab, timeout=TIMEOUT_HTTP_S)
    print(f"GET ordem {OPENMES_WORK_ORDER_ID}: HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:300])
        return
    corpo = openmes.resposta_json(r)
    ordem = corpo.get("data", corpo)
    print("status da ordem:", ordem.get("status"))
    print("campos disponíveis:", sorted(ordem.keys()))

    testaveis = [c for c in CANDIDATOS if c in ordem]
    if not testaveis:
        print("\nNenhum campo candidato aparece na leitura. Copie um campo de texto da lista acima "
              "para CANDIDATOS e execute de novo.")
        return

    for campo in testaveis:
        original = ordem.get(campo)
        r = requests.patch(url, json={campo: TEXTO_TESTE}, headers=cab, timeout=TIMEOUT_HTTP_S)
        print(f"\nPATCH {campo}: HTTP {r.status_code}")
        if r.status_code in (200, 204):
            print("  ACEITO -> use OPENMES_CAMPO_ORDEM =", repr(campo))
            restaurar = original if original is not None else ""
            r2 = requests.patch(url, json={campo: restaurar}, headers=cab, timeout=TIMEOUT_HTTP_S)
            print(f"  restaurado (HTTP {r2.status_code}); valor original: {original!r}")
            return
        print("  recusado:", r.text[:300])
    print("\nNenhum campo aceitou texto. Confira o status da ordem e as mensagens acima.")


main()