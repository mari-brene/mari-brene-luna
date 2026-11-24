"""Identidade, ajuda automática, conversa leve e easter eggs."""

import re

from ..core.personalidade import EASTER_EGGS, PIADAS, escolher
from ..core.registro import disponiveis, habilidade

_EGGS = [(re.compile(p), respostas) for p, respostas in EASTER_EGGS.items()]


@habilidade(r"\b(?:quem (?:e|eh) voce|qual (?:e )?(?:o )?seu nome|se apresente)\b",
            descricao="Apresentação", prioridade=3)
def apresentacao(ctx):
    ctx.dizer("apresentacao")


@habilidade(r"\b(?:o que voce (?:sabe|consegue) fazer|ajuda|comandos)\b", descricao="Lista comandos", prioridade=3)
def ajuda(ctx):
    exemplos = [h for h in disponiveis(ctx.plataforma) if h.exemplo]
    ctx.dizer("ajuda_intro", n=len(exemplos))
    for h in exemplos:
        ctx.falar(f"• {h.descricao}: \"{h.exemplo}\"")


@habilidade(r"\b(?:piada|me faca rir)\b", descricao="Conta piada", exemplo="Conta uma piada")
def piada(ctx):
    ctx.falar(escolher(PIADAS, "piada"))


@habilidade(r"^(?:obrigad[ao]|valeu|brigad[ao])\b", descricao="Agradecimento")
def obrigado(ctx):
    ctx.dizer("obrigado")


@habilidade(r"^(?:oi|ola|bom dia|boa tarde|boa noite|e ai)(?: tudo bem| tudo bom| como vai| beleza)?$",
            descricao="Saudação")
def saudacao(ctx):
    ctx.dizer("saudacao")


@habilidade(*EASTER_EGGS, descricao="Easter eggs", prioridade=10)
def easter_egg(ctx):
    for padrao, respostas in _EGGS:
        if padrao.search(ctx.comando_atual):
            ctx.falar(escolher(respostas, padrao.pattern))
            return
