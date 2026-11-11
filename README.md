<div align="center">

# 🏭 API Grupo B

### Integração **CODESYS → Elipse E3 + OpenMES** por um gateway Python

Monitoramento de um reservatório simulado (nível, temperatura, vazão e bomba), com
dados no supervisório e alarmes no sistema de manufatura.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![CODESYS](https://img.shields.io/badge/CODESYS-V3.5%20SP21-F26C21)
![OPC UA](https://img.shields.io/badge/OPC%20UA-asyncua-1F6FEB)
![Elipse E3](https://img.shields.io/badge/Elipse%20E3-SequenceWebService-0A7BBB)
![OpenMES](https://img.shields.io/badge/OpenMES-API%20REST-2E7D32)
![Status](https://img.shields.io/badge/projeto-acad%C3%AAmico-lightgrey)
[![Notion](https://img.shields.io/badge/Notion-documenta%C3%A7%C3%A3o-000000?logo=notion&logoColor=white)](#-notion)

[Visão geral](#-visão-geral) •
[Início rápido](#-início-rápido) •
[Configuração](#-configuração) •
[Scripts](#-scripts) •
[Problemas comuns](#-problemas-comuns) •
[Segurança](#-segurança) •
[Notion](#-notion)

</div>

---

## 📌 Visão geral

Um CLP simulado no **CODESYS** controla o nível de um reservatório. Um **gateway em Python** lê as
variáveis por **OPC UA** a cada 2 segundos e as entrega a dois destinos:

- **Elipse E3**: recebe os valores por HTTP (driver *SequenceWebService*) e os mostra em tela.
- **OpenMES**: recebe, pela **API REST**, os **alarmes de nível** (como problemas da ordem) e um
  **resumo dos valores** gravado na ordem de produção a cada 30 s.

```mermaid
flowchart LR
    A["🏭 <b>CODESYS</b><br/>Control Win V3 x64<br/>servidor OPC UA :4840"]
    B["🐍 <b>Gateway Python</b><br/>asyncua + requests<br/>lê a cada 2 s"]
    C["📊 <b>Elipse E3</b><br/>driver SequenceWebService<br/>tags e telas"]
    D["🗂️ <b>OpenMES</b><br/>ordem OP-RES-001<br/>API REST :8090"]

    A -- "OPC UA<br/>Basic256Sha256 + usuário" --> B
    B -- "HTTP POST<br/>UPDATE TAG" --> C
    B -- "REST<br/>alarmes + resumo (30 s)" --> D

    classDef main fill:#e7f1fb,stroke:#1F6FEB,stroke-width:2px,color:#111;
    classDef plain fill:#ffffff,stroke:#888,color:#111;
    class B main;
    class A,C,D plain;
```

### Variáveis monitoradas

| Variável no CODESYS | Nome no E3 (`Entity`) | Tipo | Unidade | Comportamento na simulação |
| --- | --- | --- | --- | --- |
| `GVL.rNivel` | `Nivel` | REAL | % | Começa em 50; a bomba liga com ≤ 30% e desliga com ≥ 80% |
| `GVL.rTemperatura` | `Temperatura` | REAL | °C | Oscila entre cerca de 23 e 27 |
| `GVL.rVazao` | `Vazao` | REAL | L/min | 20 com a bomba ligada, 0 desligada |
| `GVL.xBombaLigada` | `BombaLigada` | BOOL | 0 ou 1 | Estado da bomba |

### ✨ O que o projeto faz

- 🔐 Conecta ao OPC UA do CODESYS com **segurança** (`Basic256Sha256`, `SignAndEncrypt`, certificado e usuário).
- 📡 Envia as quatro variáveis ao **E3** a cada ciclo, no formato do driver SequenceWebService.
- 🚨 Registra **alarmes de nível baixo e alto** no OpenMES, com histerese e **fila de reenvio**.
- 📝 Grava um **resumo dos valores** no campo `description` da ordem, a cada 30 s.
- 🧪 Traz scripts de **diagnóstico e teste** para cada etapa, sem precisar do gateway completo.

---

## 🚀 Início rápido

### Pré-requisitos

| Item | Versão ou detalhe |
| --- | --- |
| CODESYS | V3.5 SP21 Patch 1, com o runtime **Control Win V3 x64** |
| Elipse E3 | Studio com o driver **SequenceWebService v1.0.4** instalado |
| OpenMES | Instância acessível por HTTP (neste projeto, `http://localhost:8090`) |
| Python | 3.x, com `asyncua` e `requests` |

### Instalação

```powershell
git clone https://github.com/matheusjardim-a11y/API_grupoB.git
cd API_grupoB

python -m venv .venv
.venv\Scripts\activate

pip install asyncua requests
copy config.example.py config.py      # depois, edite o config.py
```

> 💡 A biblioteca `cryptography` já vem com a `asyncua`. O `paho-mqtt` só é necessário se você ligar o MQTT (desligado por padrão).

### Passo a passo

| # | Etapa | Comando ou ação |
| :-: | --- | --- |
| 1 | **CODESYS**: criar o projeto com o código de [`codigos_codesys.txt`](codigos_codesys.txt), ligar o suporte a OPC UA na *Configuração de símbolos* e colocar o CLP em **RUN** | CODESYS |
| 2 | Gerar o certificado do cliente | `python gerar_certificado.py` |
| 3 | Aprovar o certificado: *View → Tela de segurança → Dispositivos → Quarantined → Trusted Certificates* | CODESYS |
| 4 | Preencher `USUARIO` e `SENHA` no `config.py` | editor |
| 5 | Descobrir os NodeIds e colar no `VARIAVEIS` | `python listar_nos.py` |
| 6 | Testar a leitura do CLP | `python teste_leitura.py` |
| 7 | **E3**: configurar o driver e as quatro tags, e testar o envio | `python testar_e3.py` |
| 8 | **OpenMES**: validar a API, criar a ordem e descobrir o campo de texto | `python testar_openmes.py` e `python testar_campo_ordem.py` |
| 9 | Rodar o gateway | `python gateway_codesys_e3.py` |

### Exemplo de saída do gateway

```text
INFO Conectado ao CODESYS
INFO Nivel = 37.60
INFO Temperatura = 23.64
INFO Vazao = 20.00
INFO BombaLigada = 1
INFO Ordem do OpenMES atualizada: Nível 37.6 % | Temperatura 23.6 C | Vazão 20.0 L/min | Bomba ligada | atualizado em 10/11 20:17:51
```

---

## 🔧 Configuração

Todas as opções ficam no `config.py` (copiado do `config.example.py`).

| Opção | Exemplo | Função |
| --- | --- | --- |
| `OPC_URL` | `opc.tcp://127.0.0.1:4840` | Endereço do servidor OPC UA do CODESYS |
| `USUARIO` / `SENHA` | — | Usuário e senha do dispositivo CODESYS |
| `VARIAVEIS` | `{"Nivel": "ns=4;s=..."}` | Liga cada `Entity` ao seu NodeId |
| `E3_URL` | `http://localhost:5051/` | Endereço e porta do driver no E3 |
| `ENVIAR_AO_E3` | `True` | Liga o envio ao E3 |
| `ENVIAR_AO_OPENMES` | `True` | Liga o registro de alarmes no OpenMES |
| `ATUALIZAR_ORDEM_OPENMES` | `True` | Liga o resumo na ordem, a cada 30 s |
| `OPENMES_URL` | `http://localhost:8090` | Endereço da API do OpenMES |
| `OPENMES_TOKEN` | vazio | Token fixo; vazio faz o gateway usar o login |
| `OPENMES_WORK_ORDER_ID` | `4` | Id da ordem que recebe alarmes e resumo |
| `OPENMES_ISSUE_TYPE_ID` | `11` | Tipo de problema dos alarmes (*Other Issue*) |
| `OPENMES_CAMPO_ORDEM` | `description` | Campo da ordem que recebe o resumo |
| `MODO_TESTE` | `False` | `True` usa limites de 31% e 79% para forçar alarmes |
| `ENVIAR_AO_MQTT` | `False` | Publicação MQTT (opcional, desligada) |

### 🔌 Portas usadas

| Porta | Programa | Observação |
| :-: | --- | --- |
| 4840 | Servidor OPC UA do CODESYS | |
| 5051 | Driver SequenceWebService do E3 | A padrão do driver, 8080, é ocupada pelo ScadaBR no laboratório |
| 8090 | OpenMES | |

### 🚨 Regras dos alarmes

| Alarme | Dispara quando | Rearma quando |
| --- | --- | --- |
| Nível baixo | nível ≤ 25% (31% em `MODO_TESTE`) | nível ≥ 30% (36%) |
| Nível alto | nível ≥ 90% (79% em `MODO_TESTE`) | nível ≤ 85% (74%) |

Cada ocorrência gera **um** problema na ordem. Se o OpenMES estiver fora do ar, até 20 mensagens ficam
em fila e são reenviadas no ciclo seguinte; o envio ao E3 continua normalmente.

---

## 📂 Estrutura do repositório

```text
API_grupoB/
├── 📄 README.md
├── 📄 codigos_codesys.txt        # código ST e estrutura do projeto CODESYS
├── 📄 config.example.py          # modelo do config.py (sem credenciais)
├── 🐍 gateway_codesys_e3.py      # gateway: lê o CODESYS e envia ao E3 e ao OpenMES
├── 🐍 openmes_cliente.py         # cliente da API REST do OpenMES
├── 🐍 mqtt_publicador.py         # publicação MQTT (opcional, desligada)
├── 🔐 gerar_certificado.py       # certificado do cliente OPC UA
├── 🔎 descobrir.py               # servidores e endpoints do OPC UA
├── 🔎 listar_nos.py              # NodeIds das variáveis
├── 🧪 teste_leitura.py           # leitura do CLP, sem enviar nada
├── 🧪 testar_e3.py               # envio de valores fixos ao driver do E3
├── 🧪 diagnostico_e3.py          # testa formatos de valor no E3
├── 🧪 testar_openmes.py          # saúde, token e listagens do OpenMES
├── 🧪 testar_campo_ordem.py      # descobre o campo de texto da ordem
└── 🧰 criar_produto.py           # cadastra um produto (módulo ERP do OpenMES)
```

> Ajuste os nomes e as pastas se a organização do repositório for diferente.

---

## 🧰 Scripts

| Script | Para que serve |
| --- | --- |
| `gateway_codesys_e3.py` | **Programa principal.** Lê o CODESYS e envia ao E3 e ao OpenMES |
| `gerar_certificado.py` | Cria `cliente_cert.der` e `cliente_key.pem` (uma vez) |
| `descobrir.py` | Mostra os endpoints de segurança e de usuário do servidor OPC UA |
| `listar_nos.py` | Imprime o NodeId das quatro variáveis |
| `teste_leitura.py` | Lê cinco vezes as variáveis, sem enviar nada |
| `testar_e3.py` | Envia valores fixos ao driver do E3 (resposta esperada: `Err` 0) |
| `diagnostico_e3.py` | Envia o mesmo valor em cinco formatos, para achar problemas de formato |
| `testar_openmes.py` | Valida API, token, linhas, ordens e tipos de problema; com `CRIAR_ISSUE = True` cria um problema |
| `testar_campo_ordem.py` | Descobre qual campo da ordem aceita texto e restaura o valor original |
| `criar_produto.py` | Cadastra um produto pela rota do módulo ERP (ainda não executado contra a instância) |

---

## 🐞 Problemas comuns

<details>
<summary><b>OPC UA: <code>BadServiceUnsupported</code>, <code>BadSecurityChecksFailed</code> ou <code>BadCertificateUseNotAllowed</code></b></summary>

- `BadServiceUnsupported`: o servidor só aceita conexão segura e usuário e senha. Use `criar_cliente()` do `config.py`.
- `BadSecurityChecksFailed`: o certificado está em quarentena. Mova-o para *Trusted Certificates* na Tela de segurança do CODESYS.
- `BadCertificateUseNotAllowed`: gere o certificado de novo com `gerar_certificado.py` (`MODO_CA = True`) e aprove-o outra vez.
- `BadUserAccessDenied`: `USUARIO` e `SENHA` do `config.py` ainda estão com os valores de exemplo.

</details>

<details>
<summary><b>E3: <code>Err</code> 0, mas a tela mostra <code>???</code> ou não muda</b></summary>

O `Err` 0 só confirma que o driver recebeu a requisição. Confira:

- O **Item** da tag é idêntico ao `Entity` (maiúsculas e minúsculas).
- A propriedade **`AdviseType`** das tags está em `0 - AlwaysInAdvise`.
- O projeto foi **salvo** e a aplicação foi **parada e iniciada de novo**.
- O Display da tela está ligado à tag do driver, e não a outra tag do projeto.

</details>

<details>
<summary><b>E3: a resposta é a página do Apache Tomcat, ou a conexão é recusada</b></summary>

- Página do Tomcat com HTTP 200: a porta é de outro programa (o ScadaBR usa a 8080). Troque a porta do driver e a `E3_URL`.
- `WinError 10061`: nada escuta na porta. Execute a aplicação do E3 e confira com `netstat -ano -p tcp | findstr :5051`.
- Tempo esgotado depois de reiniciar o computador: use `localhost` (mesmo computador) ou o IP da rede real.

</details>

<details>
<summary><b>OpenMES: <code>422</code>, conexão recusada ou resposta sem JSON</b></summary>

- `422` ao criar a ordem: esta versão pede `planned_qty`, e não `quantity`.
- Conexão recusada (`10061`): o OpenMES não está rodando; suba-o e confira `/api/health`.
- Login com 200 e sem JSON: a URL ou a porta estão erradas. O `testar_openmes.py` mostra a URL final e o `Content-Type`.

</details>

---

## 🔒 Segurança

> ⚠️ **Nunca envie ao GitHub** o `config.py` (usuário, senha, token) nem os arquivos do certificado
> (`cliente_key.pem` é uma chave privada). Use sempre o `config.example.py` como modelo.

Arquivo `.gitignore` sugerido:

```gitignore
config.py
cliente_key.pem
cliente_cert.der
__pycache__/
.venv/
```

Se o `config.py` já tiver sido enviado em algum commit, troque as senhas e o token que estavam nele: remover o
arquivo depois não apaga o histórico do repositório.

---

## 📓 Notion

> 🔗 **Página do projeto no Notion:** [https://app.notion.com/p/API-Reservat-rio-414adc158b2c80bd8470e1e13e3d709b?source=copy_link](https://app.notion.com/p/API-Reservat-rio-414adc158b2c80bd8470e1e13e3d709b?source=copy_link)

---

## 🚧 Limitações

- O OpenMES mostra só o **último valor**, sem histórico nem gráfico. Para telemetria contínua seria preciso o **MQTT** com um broker (o código existe, mas está desligado).
- A comunicação entre o gateway e o E3 usa **HTTP simples**, sem criptografia, em ciclos de 2 s: serve ao trabalho acadêmico, não a um controle em tempo real.
- Sem licença, o runtime **Control Win** roda em modo de demonstração por cerca de duas horas e depois exige reinício manual.
- A instância do OpenMES do grupo é **mais antiga** que a documentação publicada; nomes de campos podem divergir.

## 👥 Equipe

Projeto em grupo (**Grupo B**), SENAI.

- Ana Clara Rodrigues Abreu

- Augusto Sternadt Dziedicz

- Emanuel Coelho Lehnert

- Felipe Krueger

- Gabriel Baptista Martins

- Gustavo Engel

- Júlia Ribeiro Vansuita

- Luíza da Silva

- Matheus Scherer Jardim

- Rafael Fenilli Matosso
