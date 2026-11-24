"""
Luna — cliente desktop (terminal).

    python main.py                 # voz: diga "Luna, que horas são?"
    python main.py --sem-ativacao  # voz, sem precisar dizer "Luna"
    python main.py --texto         # teclado, sem microfone
"""

import argparse
import logging
import re

from luna.clientes.executor import ExecutorLocal
from luna.clientes.voz import ModoTexto, ModoVoz
from luna.core.assistente import Luna
from luna.core.contexto import carregar_config
from luna.core.personalidade import fala
from luna.core.sessao import Sessao
from luna.core.texto import normalizar_com_mapa, trecho_original


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
    parser.add_argument("--debug", action="store_true", help="mostra logs")
    opcoes = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if opcoes.debug else logging.WARNING)

    config = carregar_config()
    modo_texto = opcoes.texto or not config.get("voz_ativa", True)
    io = ModoTexto(config["nome"]) if modo_texto else ModoVoz(config["nome"], config["idioma"])
    luna = Luna(config, plataforma="desktop")
    executor = ExecutorLocal(io, luna.sistema)
    sessao = Sessao()
    exigir_ativacao = not (modo_texto or opcoes.sem_ativacao)
    idioma_escuta = None  # muda quando a Luna espera uma frase em outro idioma

    executor.executar(luna.saudacao(sessao, exigir_ativacao))

    while executor.rodando:
        try:
            frase = io.ouvir(idioma=idioma_escuta) if idioma_escuta else io.ouvir()
            if not frase:
                continue
            # ao responder uma pergunta da Luna, não é preciso dizer o nome dela
            if exigir_ativacao and not sessao.pendente:
                comando = extrair_comando(frase, config["palavra_ativacao"])
                if comando is None:
                    continue  # conversa no ambiente, não era comigo
                comando = comando or io.ouvir(fala("sim"))
                if not comando:
                    continue
            else:
                comando = extrair_comando(frase, config["palavra_ativacao"]) or frase
            resposta = luna.processar(comando, sessao)
            idioma_escuta = resposta.idioma_escuta
            executor.executar(resposta)
        except KeyboardInterrupt:
            executor.executar(luna.processar("encerrar", sessao))


if __name__ == "__main__":
    main()
