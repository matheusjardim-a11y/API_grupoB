"""
teste_leitura.py
Lê cinco vezes as quatro variáveis do CODESYS e imprime os valores (sem enviar nada ao E3).
"""
import asyncio

from config import VARIAVEIS, criar_cliente


async def main():
    cliente = await criar_cliente()
    async with cliente as client:
        for _ in range(5):
            for entity, node_id in VARIAVEIS.items():
                valor = await client.get_node(node_id).read_value()
                print(f"{entity}: {valor}")
            print("---")
            await asyncio.sleep(2)


asyncio.run(main())