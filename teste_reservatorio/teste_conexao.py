"""
listar_nos.py
Percorre o servidor OPC UA do CODESYS e imprime o NodeId das quatro variáveis.
Copie a saída para o dicionário VARIAVEIS em config.py.
"""
import asyncio

from config import criar_cliente

ALVO = {"rNivel", "rTemperatura", "rVazao", "xBombaLigada"}


async def percorrer(no, nivel=0, max_nivel=10):
    if nivel > max_nivel:
        return
    for filho in await no.get_children():
        nome = (await filho.read_browse_name()).Name
        if nome == "Server":              # ignora a árvore interna do servidor
            continue
        if nome in ALVO:
            print(f"{nome}  ->  {filho.nodeid.to_string()}")
        await percorrer(filho, nivel + 1, max_nivel)


async def main():
    cliente = await criar_cliente()
    async with cliente as client:
        await percorrer(client.nodes.objects)


asyncio.run(main())