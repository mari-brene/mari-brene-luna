"""
Luna — assistente virtual em Python.

    python main.py            # modo voz: diga "Luna, que horas são?"
    python main.py --texto    # modo texto: digite os comandos (sem microfone)
"""

import argparse
import re

from luna import habilidades  # noqa: F401  (registra as habilidades)
from luna.core.personalidade import fala
from luna.core.contexto import Contexto, carregar_config
from luna.core.registro import encontrar
from luna.core.texto import normalizar_com_mapa, trecho_original
from luna.core.voz import ModoTexto, ModoVoz


def executar(ctx: Contexto, frase: str) -> None:
    hab, args, comando = encontrar(frase)
    ctx.comando_atual = comando
    if not hab:
        ctx.dizer("nao_entendi")
        return
    try:
        hab.funcao(ctx, **args)
    except Exception as erro:  # uma habilidade com erro não derruba a assistente
        print(f"  [erro em {hab.funcao.__name__}: {erro!r}]")
        ctx.dizer("erro")


def extrair_comando(frase: str, ativacao: str) -> str | None:
    """Devolve (no texto original) o que vem depois da palavra de ativação, ou None se ela não foi dita."""
    comando, mapa = normalizar_com_mapa(frase)
    achou = re.search(rf"\b{ativacao}\b ?", comando)
    if not achou:
        return None
    return trecho_original(frase, mapa, achou.end(), len(comando))


def main() -> None:
    parser = argparse.ArgumentParser(description="Luna, assistente virtual")
    parser.add_argument("--texto", action="store_true", help="usar teclado em vez de microfone")
    parser.add_argument("--sem-ativacao", action="store_true", help="não exigir 'Luna' antes do comando")
    opcoes = parser.parse_args()

    config = carregar_config()
    modo_texto = opcoes.texto or not config.get("voz_ativa", True)
    io = ModoTexto(config["nome"]) if modo_texto else ModoVoz(config["nome"], config["idioma"])
    ctx = Contexto(config=config, io=io)
    exigir_ativacao = not (modo_texto or opcoes.sem_ativacao)

    ctx.dizer("boas_vindas" if exigir_ativacao else "boas_vindas_texto")

    while ctx.rodando:
        try:
            frase = ctx.ouvir()
            if not frase:
                continue
            if exigir_ativacao:
                comando = extrair_comando(frase, config["palavra_ativacao"])
                if comando is None:
                    continue  # conversa no ambiente, não era comigo
                comando = comando or ctx.ouvir(fala("sim"))
                if not comando:
                    continue
            else:
                comando = extrair_comando(frase, config["palavra_ativacao"]) or frase
            executar(ctx, comando)
        except KeyboardInterrupt:
            executar(ctx, "encerrar")


if __name__ == "__main__":
    main()
