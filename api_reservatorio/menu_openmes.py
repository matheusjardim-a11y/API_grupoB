"""
menu_openmes.py
Menu interativo para operar o OpenMES pela API: listar dados, criar produto, criar work order,
registrar problema (issue) e editar o texto de uma ordem.

Usa as opções OPENMES_* do config.py e o cliente openmes_cliente.py.
Para cadastrar produtos (rota ERP) é preciso uma chave de API: defina OPENMES_API_KEY no config.py
(Settings > API Keys, escopo erp:masterdata:write) ou digite-a quando o menu pedir.

Uso:  python menu_openmes.py
"""
import json

import requests

import config
import openmes_cliente as openmes

URL = config.OPENMES_URL
TIMEOUT = config.TIMEOUT_HTTP_S
API_KEY = getattr(config, "OPENMES_API_KEY", "")   # opcional: só se existir Settings > API Keys


# ---------------- utilitários ----------------
def perguntar(texto, padrao=None, obrigatorio=False):
    """Lê um texto; Enter aceita o padrão. Repete se for obrigatório e vier vazio."""
    sufixo = f" [{padrao}]" if padrao not in (None, "") else ""
    while True:
        valor = input(f"{texto}{sufixo}: ").strip()
        if valor:
            return valor
        if padrao not in (None, ""):
            return str(padrao)
        if not obrigatorio:
            return ""
        print("  Campo obrigatório.")


def perguntar_numero(texto, padrao=None, obrigatorio=False):
    """Lê um número (inteiro ou decimal); devolve None se opcional e vazio."""
    while True:
        bruto = perguntar(texto, padrao, obrigatorio)
        if not bruto:
            return None
        try:
            numero = float(bruto.replace(",", "."))
            return int(numero) if numero.is_integer() else numero
        except ValueError:
            print("  Digite um número.")


def confirmar(texto):
    return input(f"{texto} (s/N): ").strip().lower() in ("s", "sim")


def mostrar_resposta(resp):
    print(f"\n  HTTP {resp.status_code}")
    try:
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:1500])
    except ValueError:
        print("  ", (resp.text or "")[:500])


def listar(caminho):
    """GET autenticado; devolve a lista da chave 'data' (ou None se falhar)."""
    resp = openmes._chamar("GET", caminho, None)
    if resp.status_code != 200:
        print(f"\n  Falha ao listar {caminho}: HTTP {resp.status_code} {resp.text[:200]!r}")
        return None
    corpo = openmes.resposta_json(resp)
    dados = corpo.get("data", corpo) if isinstance(corpo, dict) else corpo
    return dados if isinstance(dados, list) else []


def imprimir_lista(titulo, caminho, campos):
    itens = listar(caminho)
    if itens is None:
        return None
    print(f"\n== {titulo} ({len(itens)})")
    for item in itens:
        print("  ", " | ".join(str(item.get(c)) for c in campos))
    return itens


# ---------------- ações ----------------
def acao_verificar():
    print("\n  API:", openmes.verificar_api())
    print("  Token obtido:", openmes.obter_token()[:6] + "...")


def acao_listar_linhas():
    imprimir_lista("Linhas", "/api/v1/lines", ("id", "code", "name"))


def acao_listar_ordens():
    imprimir_lista("Work orders", "/api/v1/work-orders?per_page=50",
                   ("id", "order_no", "status", "planned_qty", "product_type_id"))


def acao_listar_tipos_problema():
    imprimir_lista("Tipos de problema", "/api/v1/issue-types", ("id", "name", "is_critical"))


def acao_listar_produtos():
    itens = imprimir_lista("Produtos (product types)", "/api/v1/product-types",
                           ("id", "code", "name"))
    if itens is None:
        print("  Se a rota não existir nesta versão, confira os produtos na tela Product Types.")


def acao_criar_produto():
    """Tenta, nesta ordem: importação ERP com chave de API (se houver), importação ERP com o token
    de login e cadastro direto em /api/v1/product-types. Mostra a resposta de cada tentativa."""
    print("\n== Criar produto")
    produto = {
        "code": perguntar("Código do produto", obrigatorio=True),
        "name": perguntar("Nome", obrigatorio=True),
        "category": perguntar("Categoria (FINISHED, SEMI...)", "FINISHED"),
        "unit_of_measure": perguntar("Unidade de medida (ex.: pcs)", "pcs"),
    }
    descricao = perguntar("Descrição (opcional)")
    if descricao:
        produto["description"] = descricao
    if not confirmar(f"Enviar produto '{produto['code']}'?"):
        return print("  Cancelado.")
    importacao = {"strategy": "update_or_create", "external_system": "menu-openmes", "products": [produto]}
    cab = {"Accept": "application/json"}

    tentativas = []
    if API_KEY:
        tentativas.append(("importação ERP com chave de API", "/api/v1/erp/products/import",
                           importacao, {**cab, "X-Api-Key": API_KEY}))
    tentativas.append(("importação ERP com o token de login", "/api/v1/erp/products/import",
                       importacao, {**cab, "Authorization": f"Bearer {openmes.obter_token()}"}))
    tentativas.append(("cadastro direto em product-types", "/api/v1/product-types",
                       produto, {**cab, "Authorization": f"Bearer {openmes.obter_token()}"}))

    for nome, caminho, corpo, cabecalhos in tentativas:
        print(f"\n-- Tentativa: {nome}")
        resp = requests.post(f"{URL}{caminho}", json=corpo, headers=cabecalhos, timeout=TIMEOUT)
        mostrar_resposta(resp)
        if resp.status_code in (200, 201, 207):
            return print("  Produto enviado. Confira em Product Types no OpenMES.")
    print("\n  Nenhuma rota aceitou. Cadastre o produto pela tela Product Types (ou pela importação de CSV)")
    print("  e, se quiser, envie as respostas acima para ajustarmos os campos.")


def acao_criar_ordem():
    print("\n== Criar work order")
    linhas = imprimir_lista("Linhas disponíveis", "/api/v1/lines", ("id", "code", "name"))
    produtos = imprimir_lista("Produtos disponíveis", "/api/v1/product-types", ("id", "code", "name"))
    corpo = {"order_no": perguntar("Número da ordem (ex.: OP-RES-002)", obrigatorio=True)}
    linha = perguntar_numero("Id da linha" + ("" if linhas else " (opcional)"), obrigatorio=bool(linhas))
    produto = perguntar_numero("Id do produto (product_type_id)" + ("" if produtos else " (opcional)"),
                               obrigatorio=bool(produtos))
    corpo["planned_qty"] = perguntar_numero("Quantidade planejada", 1, obrigatorio=True)
    if linha is not None:
        corpo["line_id"] = linha
    if produto is not None:
        corpo["product_type_id"] = produto
    inicio = perguntar("Início planejado (AAAA-MM-DDTHH:MM:SS, opcional)")
    if inicio:
        corpo["planned_start_at"] = inicio
    prioridade = perguntar("Prioridade (opcional)")
    if prioridade:
        corpo["priority"] = prioridade
    descricao = perguntar("Descrição (opcional)")
    if descricao:
        corpo["description"] = descricao
    print("\n  Será enviado:", json.dumps(corpo, ensure_ascii=False))
    if not confirmar("Criar a ordem?"):
        return print("  Cancelado.")
    resp = openmes._chamar("POST", "/api/v1/work-orders", corpo)
    mostrar_resposta(resp)
    if resp.status_code == 422:
        print("  O OpenMES recusou algum campo: leia a mensagem acima, ajuste e tente de novo.")


def acao_criar_problema():
    print("\n== Registrar problema (issue) em uma ordem")
    imprimir_lista("Work orders", "/api/v1/work-orders?per_page=50", ("id", "order_no", "status"))
    tipos = imprimir_lista("Tipos de problema", "/api/v1/issue-types", ("id", "name"))
    ordem = perguntar_numero("Id da work order", config.OPENMES_WORK_ORDER_ID, True)
    tipo = perguntar_numero("Id do tipo de problema", config.OPENMES_ISSUE_TYPE_ID, True)
    titulo = perguntar("Título do problema", obrigatorio=True)
    descricao = perguntar("Descrição (opcional)", titulo)
    corpo = {"work_order_id": ordem, "issue_type_id": tipo, "title": titulo, "description": descricao}
    if not confirmar("Registrar o problema?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("POST", "/api/v1/issues", corpo))


def acao_editar_ordem():
    print("\n== Editar texto de uma work order (PATCH)")
    imprimir_lista("Work orders", "/api/v1/work-orders?per_page=50", ("id", "order_no", "status"))
    ordem = perguntar_numero("Id da work order", config.OPENMES_WORK_ORDER_ID, True)
    campo = perguntar("Campo", getattr(config, "OPENMES_CAMPO_ORDEM", "description"))
    texto = perguntar("Novo texto", obrigatorio=True)
    print("  Só funciona em ordens 'pending' ou 'accepted'.")
    if not confirmar(f"Gravar em '{campo}' da ordem {ordem}?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("PATCH", f"/api/v1/work-orders/{ordem}", {campo: texto}))


def _escolher_ordem(texto="Id da work order"):
    imprimir_lista("Work orders", "/api/v1/work-orders?per_page=50", ("id", "order_no", "status"))
    return perguntar_numero(texto, config.OPENMES_WORK_ORDER_ID, True)


def acao_detalhar_ordem():
    print("\n== Detalhes de uma work order")
    ordem = _escolher_ordem()
    mostrar_resposta(openmes._chamar("GET", f"/api/v1/work-orders/{ordem}", None))


def acao_listar_problemas():
    print("\n== Problemas (issues) registrados")
    itens = imprimir_lista("Problemas", "/api/v1/issues?per_page=50",
                           ("id", "work_order_id", "issue_type_id", "title", "status"))
    if itens is None:
        print("  Se a rota de listagem não existir nesta versão, use a opção de requisição livre.")


def acao_alterar_status():
    print("\n== Alterar status de uma work order (PATCH)")
    ordem = _escolher_ordem()
    status = perguntar("Novo status (ex.: ACCEPTED, DONE, CANCELLED)", obrigatorio=True).upper()
    print("  O OpenMES pode recusar transições que não sejam permitidas a partir do status atual.")
    if not confirmar(f"Mudar a ordem {ordem} para '{status}'?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("PATCH", f"/api/v1/work-orders/{ordem}", {"status": status}))


def acao_cancelar_ordem():
    print("\n== Cancelar uma work order")
    ordem = _escolher_ordem()
    if not confirmar(f"Cancelar a ordem {ordem}? Isso pode não ter volta"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("PATCH", f"/api/v1/work-orders/{ordem}", {"status": "CANCELLED"}))


def acao_editar_produto():
    print("\n== Editar produto (PATCH)")
    imprimir_lista("Produtos", "/api/v1/product-types", ("id", "code", "name"))
    produto = perguntar_numero("Id do produto", obrigatorio=True)
    corpo = {}
    for campo, rotulo in (("name", "Novo nome"), ("description", "Nova descrição"),
                          ("unit_of_measure", "Nova unidade de medida")):
        valor = perguntar(f"{rotulo} (Enter mantém)")
        if valor:
            corpo[campo] = valor
    if not corpo:
        return print("  Nada a alterar.")
    print("  Será enviado:", json.dumps(corpo, ensure_ascii=False))
    if not confirmar("Gravar?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("PATCH", f"/api/v1/product-types/{produto}", corpo))


def acao_criar_linha():
    print("\n== Criar linha de produção")
    corpo = {"code": perguntar("Código da linha", obrigatorio=True),
             "name": perguntar("Nome da linha", obrigatorio=True)}
    descricao = perguntar("Descrição (opcional)")
    if descricao:
        corpo["description"] = descricao
    if not confirmar(f"Criar a linha '{corpo['code']}'?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("POST", "/api/v1/lines", corpo))


def acao_criar_tipo_problema():
    print("\n== Criar tipo de problema")
    corpo = {"name": perguntar("Nome do tipo", obrigatorio=True)}
    if confirmar("É crítico (is_critical)?"):
        corpo["is_critical"] = True
    if not confirmar(f"Criar o tipo '{corpo['name']}'?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("POST", "/api/v1/issue-types", corpo))


def acao_excluir():
    print("\n== Excluir um registro (DELETE)")
    recursos = {"1": ("work order", "/api/v1/work-orders"), "2": ("produto", "/api/v1/product-types"),
                "3": ("linha", "/api/v1/lines"), "4": ("problema", "/api/v1/issues")}
    for k, (nome, _) in recursos.items():
        print(f"  {k}. {nome}")
    escolha = perguntar("Tipo de registro", obrigatorio=True)
    if escolha not in recursos:
        return print("  Opção inválida.")
    nome, base = recursos[escolha]
    identificador = perguntar_numero(f"Id do(a) {nome}", obrigatorio=True)
    if input(f"Digite EXCLUIR para apagar {nome} {identificador}: ").strip() != "EXCLUIR":
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar("DELETE", f"{base}/{identificador}", None))


def acao_requisicao_livre():
    print("\n== Requisição livre (avançado)")
    metodo = perguntar("Método (GET, POST, PATCH)", "GET").upper()
    caminho = perguntar("Caminho (ex.: /api/v1/lines)", obrigatorio=True)
    corpo = None
    if metodo in ("POST", "PATCH"):
        bruto = perguntar("Corpo em JSON", "{}")
        try:
            corpo = json.loads(bruto)
        except ValueError:
            return print("  JSON inválido.")
    if metodo != "GET" and not confirmar(f"Enviar {metodo} {caminho}?"):
        return print("  Cancelado.")
    mostrar_resposta(openmes._chamar(metodo, caminho, corpo))


# ---------------- menu ----------------
MENU = [
    ("Verificar API e login", acao_verificar),
    ("Listar linhas", acao_listar_linhas),
    ("Listar work orders", acao_listar_ordens),
    ("Listar tipos de problema", acao_listar_tipos_problema),
    ("Listar produtos", acao_listar_produtos),
    ("Listar problemas (issues) registrados", acao_listar_problemas),
    ("Detalhar uma work order", acao_detalhar_ordem),
    ("Criar produto", acao_criar_produto),
    ("Criar work order", acao_criar_ordem),
    ("Criar linha de produção", acao_criar_linha),
    ("Criar tipo de problema", acao_criar_tipo_problema),
    ("Registrar problema (issue) em uma ordem", acao_criar_problema),
    ("Editar texto de uma work order", acao_editar_ordem),
    ("Alterar status de uma work order", acao_alterar_status),
    ("Cancelar uma work order", acao_cancelar_ordem),
    ("Editar produto", acao_editar_produto),
    ("Excluir um registro", acao_excluir),
    ("Requisição livre (avançado)", acao_requisicao_livre),
]


def main():
    print(f"OpenMES em {URL}")
    while True:
        print("\n===== Menu OpenMES =====")
        for i, (titulo, _) in enumerate(MENU, 1):
            print(f" {i:>2}. {titulo}")
        print("  0. Sair")
        escolha = input("Opção: ").strip()
        if escolha == "0":
            break
        if not escolha.isdigit() or not 1 <= int(escolha) <= len(MENU):
            print("Opção inválida.")
            continue
        try:
            MENU[int(escolha) - 1][1]()
        except (openmes.ErroOpenMES, requests.RequestException) as erro:
            print("\n  FALHA:", erro)
        except (KeyboardInterrupt, EOFError):
            print("\n  Operação interrompida.")


if __name__ == "__main__":
    main()