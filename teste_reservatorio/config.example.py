"""
config.example.py
MODELO do config.py. Este arquivo vai para o GitHub; o config.py (com as senhas) NÃO.

Como usar:
  1. Copie este arquivo para config.py (na mesma pasta);
  2. Preencha os campos marcados com < >;
  3. Nunca envie o config.py ao repositório (ele está no .gitignore).
"""
import os

from asyncua import Client

PASTA = os.path.dirname(os.path.abspath(__file__))

# ---------------- CODESYS (servidor OPC UA) ----------------
OPC_URL = "opc.tcp://127.0.0.1:4840"
USUARIO = "<usuario-do-dispositivo>"        # usuário do dispositivo no CODESYS
SENHA = "<senha-do-dispositivo>"

# Certificado do cliente (gerado por gerar_certificado.py; NÃO vão para o GitHub)
APP_URI = "urn:reservatorio:gateway"
CERT = os.path.join(PASTA, "cliente_cert.der")
CHAVE = os.path.join(PASTA, "cliente_key.pem")

# Entity no E3  ->  NodeId no CODESYS
# Confira os NodeIds com listar_nos.py (o nome do dispositivo pode mudar)
VARIAVEIS = {
    "Nivel":       "ns=4;s=|var|CODESYS Control Win V3 x64.Application.GVL.rNivel",
    "Temperatura": "ns=4;s=|var|CODESYS Control Win V3 x64.Application.GVL.rTemperatura",
    "Vazao":       "ns=4;s=|var|CODESYS Control Win V3 x64.Application.GVL.rVazao",
    "BombaLigada": "ns=4;s=|var|CODESYS Control Win V3 x64.Application.GVL.xBombaLigada",
}

# ---------------- Elipse E3 (driver SequenceWebService) ----------------
# Mesma porta configurada no driver (aba SequenceWebService). Se o gateway rodar em outro
# computador, troque localhost pelo IP da rede do computador do E3.
E3_URL = "http://localhost:<porta-do-driver>/"

# ---------------- Destinos do gateway ----------------
ENVIAR_AO_E3 = True
ENVIAR_AO_OPENMES = True

# ---------------- OpenMES (API REST) ----------------
OPENMES_URL = "http://<ip-ou-host>:<porta>"      # sem barra no final
OPENMES_TOKEN = ""                               # token de Settings > API Tokens (opcional)
OPENMES_USUARIO = "<usuario>"                    # usados só se OPENMES_TOKEN estiver vazio
OPENMES_SENHA = "<senha>"
OPENMES_WORK_ORDER_ID = 0                        # id numérico da work order do reservatório
OPENMES_ISSUE_TYPE_ID = 0                        # id do tipo de problema que recebe os alarmes

# ---------------- MQTT (opcional; desligado) ----------------
ENVIAR_AO_MQTT = False
MQTT_HOST = "localhost"
MQTT_PORTA = 1883
MQTT_USUARIO = ""                      # vazio = sem autenticação (broker de teste)
MQTT_SENHA = ""
MQTT_TOPICO = "reservatorio/tanque01/status"
MQTT_INTERVALO_S = 5.0

# ---------------- Resumo dos valores na Work Order do OpenMES (API REST) ----------------
ATUALIZAR_ORDEM_OPENMES = True         # True: grava um resumo das variáveis em um campo da ordem
OPENMES_CAMPO_ORDEM = "description"    # campo aceito pela sua versão (veja testar_campo_ordem.py)
OPENMES_INTERVALO_ORDEM_S = 30.0       # cada atualização gera registro de auditoria

# ---------------- Alarmes de nível ----------------
MODO_TESTE = False         # True: limites dentro da faixa da simulação (31 e 79), para forçar alarmes
LIMITE_NIVEL_BAIXO = 25.0  # alarme quando o nível fica igual ou abaixo (%)
LIMITE_NIVEL_ALTO = 90.0   # alarme quando o nível fica igual ou acima (%)
HISTERESE_ALARME = 5.0     # o alarme só rearma depois que o nível volta 5 pontos para dentro

# ---------------- Gateway ----------------
INTERVALO_S = 2.0
TIMEOUT_HTTP_S = 5


async def criar_cliente():
    """Cria o cliente OPC UA com segurança (Basic256Sha256, SignAndEncrypt) e usuário/senha."""
    cliente = Client(url=OPC_URL, timeout=10)
    cliente.application_uri = APP_URI
    cliente.set_user(USUARIO)
    cliente.set_password(SENHA)
    await cliente.set_security_string(f"Basic256Sha256,SignAndEncrypt,{CERT},{CHAVE}")
    return cliente