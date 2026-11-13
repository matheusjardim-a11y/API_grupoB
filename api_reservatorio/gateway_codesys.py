"""
gateway_codesys_e3.py
Lê as variáveis do CODESYS (OPC UA) e:
  - envia cada uma ao Elipse E3 (driver SequenceWebService, HTTP POST), a cada ciclo;
  - registra no OpenMES (API REST) os alarmes de nível, somente quando ocorrem;
  - (opcional) grava um resumo das variáveis em um campo da Work Order, por API REST;
  - (opcional) publica as leituras em um broker MQTT, de onde o OpenMES as coleta.
"""
import asyncio
import logging
import time
from datetime import datetime

import requests

import config
import openmes_cliente as openmes
from config import E3_URL, INTERVALO_S, TIMEOUT_HTTP_S, VARIAVEIS, criar_cliente


def _opcao(nome, padrao):
    """Lê uma opção do config.py; se ela não existir, usa o padrão (evita ImportError)."""
    return getattr(config, nome, padrao)


ENVIAR_AO_E3 = _opcao("ENVIAR_AO_E3", True)
ENVIAR_AO_OPENMES = _opcao("ENVIAR_AO_OPENMES", False)
ATUALIZAR_ORDEM_OPENMES = _opcao("ATUALIZAR_ORDEM_OPENMES", False)
ENVIAR_AO_MQTT = _opcao("ENVIAR_AO_MQTT", False)
OPENMES_CAMPO_ORDEM = _opcao("OPENMES_CAMPO_ORDEM", "description")
OPENMES_INTERVALO_ORDEM_S = _opcao("OPENMES_INTERVALO_ORDEM_S", 30.0)
MODO_TESTE = _opcao("MODO_TESTE", False)
LIMITE_NIVEL_BAIXO = _opcao("LIMITE_NIVEL_BAIXO", 25.0)
LIMITE_NIVEL_ALTO = _opcao("LIMITE_NIVEL_ALTO", 90.0)
HISTERESE_ALARME = _opcao("HISTERESE_ALARME", 5.0)

if ENVIAR_AO_MQTT:
    from mqtt_publicador import PublicadorMQTT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway")
logging.getLogger("asyncua").setLevel(logging.WARNING)


def formatar(valor):
    """Converte o valor lido para o texto enviado ao E3 (bomba: 1/0)."""
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


def enviar_ao_e3(entity, valor):
    """POST no formato esperado pelo driver SequenceWebService (operação UPDATE TAG)."""
    corpo = {
        "Value": formatar(valor),
        "Quality": 192,
        "Time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),   # ISO 8601, como no formato do driver
    }
    cabecalhos = {
        "Content-Type": "application/json",
        "Operation": "UPDATE TAG",
        "Entity": entity,
    }
    resp = requests.post(E3_URL, json=corpo, headers=cabecalhos, timeout=TIMEOUT_HTTP_S)
    resp.raise_for_status()
    retorno = resp.json()
    if retorno.get("Err") != 0:
        raise RuntimeError(f"E3 recusou '{entity}': {retorno}")


class MonitorAlarmes:
    """Detecta alarmes de nível com histerese: uma mensagem por ocorrência, não por leitura."""

    def __init__(self):
        self.baixo, self.alto = (31.0, 79.0) if MODO_TESTE else (LIMITE_NIVEL_BAIXO, LIMITE_NIVEL_ALTO)
        self.baixo_ativo = False
        self.alto_ativo = False
        self.fila = []                       # mensagens ainda não aceitas pelo OpenMES

    def registrar(self, valores):
        nivel = float(valores["Nivel"])
        if not self.baixo_ativo and nivel <= self.baixo:
            self.baixo_ativo = True
            self._enfileirar("Nível baixo", valores)
        elif self.baixo_ativo and nivel >= self.baixo + HISTERESE_ALARME:
            self.baixo_ativo = False

        if not self.alto_ativo and nivel >= self.alto:
            self.alto_ativo = True
            self._enfileirar("Nível alto", valores)
        elif self.alto_ativo and nivel <= self.alto - HISTERESE_ALARME:
            self.alto_ativo = False

    def _enfileirar(self, titulo, valores):
        bomba = "ligada" if valores["BombaLigada"] else "desligada"
        texto = (f"{titulo} no reservatório | Nível {float(valores['Nivel']):.1f} % | "
                 f"Temperatura {float(valores['Temperatura']):.1f} C | "
                 f"Vazão {float(valores['Vazao']):.1f} L/min | Bomba {bomba}")
        self.fila.append(texto)
        if len(self.fila) > 20:              # evita crescer sem limite se o OpenMES ficar fora do ar
            self.fila.pop(0)


class AtualizadorOrdem:
    """Grava um resumo das variáveis em um campo da Work Order, no máximo a cada N segundos."""

    def __init__(self):
        self._ultimo = 0.0

    @staticmethod
    def resumo(valores):
        bomba = "ligada" if valores["BombaLigada"] else "desligada"
        return (f"Nível {float(valores['Nivel']):.1f} % | Temperatura {float(valores['Temperatura']):.1f} C | "
                f"Vazão {float(valores['Vazao']):.1f} L/min | Bomba {bomba} | "
                f"atualizado em {datetime.now().strftime('%d/%m %H:%M:%S')}")

    async def atualizar_se_devido(self, valores):
        agora = time.monotonic()
        if agora - self._ultimo < OPENMES_INTERVALO_ORDEM_S:
            return
        self._ultimo = agora
        texto = self.resumo(valores)
        try:
            await asyncio.to_thread(openmes.atualizar_ordem, OPENMES_CAMPO_ORDEM, texto)
            log.info("Ordem do OpenMES atualizada: %s", texto)
        except (openmes.ErroOpenMES, requests.RequestException) as erro:
            log.warning("Falha ao atualizar a ordem no OpenMES: %s", erro)


async def enviar_alarmes_pendentes(monitor):
    while monitor.fila:
        texto = monitor.fila[0]
        try:
            await asyncio.to_thread(openmes.criar_issue, texto)
        except (openmes.ErroOpenMES, requests.RequestException) as erro:
            log.warning("Falha ao registrar alarme no OpenMES (nova tentativa no próximo ciclo): %s", erro)
            return
        monitor.fila.pop(0)
        log.info("Alarme registrado no OpenMES: %s", texto)


async def ciclo(monitor, publicador, atualizador):
    cliente = await criar_cliente()
    async with cliente as client:
        nos = {entity: client.get_node(node_id) for entity, node_id in VARIAVEIS.items()}
        log.info("Conectado ao CODESYS")
        while True:
            valores = {entity: await no.read_value() for entity, no in nos.items()}

            if ENVIAR_AO_E3:
                for entity, valor in valores.items():
                    try:
                        await asyncio.to_thread(enviar_ao_e3, entity, valor)
                        log.info("%s = %s", entity, formatar(valor))
                    except (requests.RequestException, RuntimeError, ValueError) as erro:
                        log.warning("Falha ao enviar %s ao E3: %s", entity, erro)

            if ENVIAR_AO_OPENMES:
                monitor.registrar(valores)
                await enviar_alarmes_pendentes(monitor)

            if atualizador:
                await atualizador.atualizar_se_devido(valores)

            if publicador:
                publicador.publicar_se_devido(valores)

            await asyncio.sleep(INTERVALO_S)


async def main():
    monitor = MonitorAlarmes()
    log.info("Destinos ativos -> E3: %s | alarmes no OpenMES: %s | resumo na ordem: %s | MQTT: %s",
             ENVIAR_AO_E3, ENVIAR_AO_OPENMES, ATUALIZAR_ORDEM_OPENMES, ENVIAR_AO_MQTT)
    atualizador = AtualizadorOrdem() if ATUALIZAR_ORDEM_OPENMES else None
    publicador = None
    if ENVIAR_AO_MQTT:
        publicador = PublicadorMQTT()
        publicador.conectar()
    if ENVIAR_AO_OPENMES:
        try:
            dados = await asyncio.to_thread(openmes.verificar_api)
            log.info("OpenMES acessível: %s", dados)
        except (openmes.ErroOpenMES, requests.RequestException) as erro:
            log.warning("OpenMES indisponível na partida: %s", erro)
    while True:
        try:
            await ciclo(monitor, publicador, atualizador)
        except Exception as erro:            # perda de conexão OPC UA, etc.
            if "BadUserAccessDenied" in str(erro) or "BadIdentityTokenRejected" in str(erro):
                log.error("CODESYS recusou o usuário/senha (confira USUARIO e SENHA no config.py). "
                          "Nova tentativa em 60 s.")
                await asyncio.sleep(60)
            else:
                log.error("Falha: %s. Nova tentativa em 5 s.", erro)
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())