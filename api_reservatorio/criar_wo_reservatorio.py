import requests

import openmes_cliente as openmes
from config import OPENMES_URL, TIMEOUT_HTTP_S

cab = {"Authorization": f"Bearer {openmes.obter_token()}", "Accept": "application/json"}
corpo = {"order_no": "OP-RES-002", "product_name": "Reservatório (integração CODESYS)", "planned_qty": 1}
r = requests.post(f"{OPENMES_URL}/api/v1/work-orders", json=corpo, headers=cab, timeout=TIMEOUT_HTTP_S)
print(r.status_code, r.text[:400])