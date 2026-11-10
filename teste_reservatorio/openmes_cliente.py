"""
openmes_cliente.py
Cliente mínimo da API REST do OpenMES: autenticação (token fixo ou login) e criação de issues.
"""
import logging

import requests

from config import (OPENMES_ISSUE_TYPE_ID, OPENMES_SENHA, OPENMES_TOKEN, OPENMES_URL,
                    OPENMES_USUARIO, OPENMES_WORK_ORDER_ID, TIMEOUT_HTTP_S)

log = logging.getLogger("openmes")
_token_em_cache = OPENMES_TOKEN


class ErroOpenMES(Exception):
    """Falha de comunicação ou resposta inesperada do OpenMES."""


def resposta_json(resp):
    """Converte a resposta em JSON; se não for JSON, explica o que veio no lugar."""
    try:
        return resp.json()
    except ValueError:
        trecho = resp.text[:200].replace("\n", " ")
        raise ErroOpenMES(
            f"Resposta sem JSON (HTTP {resp.status_code}, "
            f"Content-Type '{resp.headers.get('Content-Type', '')}', URL final {resp.url}): {trecho!r}"
        )


def verificar_api():
    """GET /api/health: confirma que a URL aponta para a API do OpenMES."""
    resp = requests.get(f"{OPENMES_URL}/api/health", headers={"Accept": "application/json"},
                        timeout=TIMEOUT_HTTP_S)
    dados = resposta_json(resp)
    if dados.get("status") != "ok":
        raise ErroOpenMES(f"Resposta inesperada em /api/health: {dados}")
    return dados


def obter_token(forcar=False):
    """Token fixo (OPENMES_TOKEN) ou login em /api/auth/login, com cache."""
    global _token_em_cache
    if _token_em_cache and not forcar:
        return _token_em_cache
    resp = requests.post(
        f"{OPENMES_URL}/api/auth/login",
        json={"username": OPENMES_USUARIO, "password": OPENMES_SENHA},
        headers={"Accept": "application/json"},
        timeout=TIMEOUT_HTTP_S,
    )
    if resp.status_code != 200:
        raise ErroOpenMES(f"Login recusado (HTTP {resp.status_code}): {resp.text[:200]!r}")
    token = resposta_json(resp).get("token")
    if not token:
        raise ErroOpenMES("Resposta do login sem o campo 'token'")
    _token_em_cache = token
    return token


def _chamar(metodo, caminho, corpo):
    """Chamada autenticada à API; refaz o login uma vez se o token for recusado (401)."""
    for tentativa in (1, 2):
        cabecalhos = {"Authorization": f"Bearer {obter_token()}", "Accept": "application/json"}
        resp = requests.request(metodo, f"{OPENMES_URL}{caminho}", json=corpo, headers=cabecalhos,
                                timeout=TIMEOUT_HTTP_S)
        if resp.status_code == 401 and tentativa == 1 and not OPENMES_TOKEN:
            obter_token(forcar=True)         # token expirado ou revogado
            continue
        break
    return resp


def criar_issue(descricao):
    """POST /api/v1/issues. Lança ErroOpenMES se o OpenMES recusar."""
    corpo = {
        "work_order_id": OPENMES_WORK_ORDER_ID,
        "issue_type_id": OPENMES_ISSUE_TYPE_ID,
        "description": descricao,
    }
    resp = _chamar("POST", "/api/v1/issues", corpo)
    if resp.status_code not in (200, 201):
        raise ErroOpenMES(f"Issue recusado (HTTP {resp.status_code}): {resp.text[:300]!r}")
    return resposta_json(resp)


def atualizar_ordem(campo, texto):
    """PATCH /api/v1/work-orders/{id}: grava o texto em um campo da ordem.
    A documentação indica que a edição só vale para ordens em 'pending' ou 'accepted'."""
    resp = _chamar("PATCH", f"/api/v1/work-orders/{OPENMES_WORK_ORDER_ID}", {campo: texto})
    if resp.status_code not in (200, 204):
        raise ErroOpenMES(f"Atualização da ordem recusada (HTTP {resp.status_code}): {resp.text[:300]!r}")
    return resp