"""
Abrir programas, agendar/cancelar desligamento e encerrar a assistente.

As habilidades só decidem O QUE fazer e devolvem uma ação; quem executa é o
cliente desktop (luna/clientes/executor.py). Na web elas não existem, e uma
habilidade substituta explica isso.
"""

import os

from ..core.registro import habilidade
from ..core.texto import normalizar, para_numero

_ABRIR = r"^(?:abrir?|abra|inicia[r]?) (?:o |a )?(?P<alvo>.+)$"
_DESLIGAR = (
    r"\bdesligar? (?:o )?(?:computador|pc)(?: em| daqui a)? (?P<qtd>[\w,.]+)? ?(?P<unidade>minuto|hora)s?",
    r"\bdesligar? (?:o )?(?:computador|pc) em (?P<qtd>meia) (?P<unidade>hora)",
)


@habilidade(_ABRIR, descricao="Abre programas", exemplo="Abrir Discord",
            prioridade=-2, livres=("alvo",), plataformas=("desktop",))
def abrir(ctx, alvo):
    programas = ctx.config["programas"]
    nome = normalizar(alvo)
    chave = ctx.config.get("apelidos_programas", {}).get(nome, nome).replace(" ", "")
    comando = programas.get(chave, {}).get(ctx.sistema)
    if not comando:
        ctx.dizer("abrir_desconhecido", alvo=alvo)
        return
    ctx.acao("abrir_programa", comando=os.path.expandvars(comando), nome=alvo)
    ctx.dizer("abrir_ok", alvo=alvo)


@habilidade(*_DESLIGAR, descricao="Agenda desligamento", exemplo="Desligar o computador em 40 minutos",
            prioridade=4, plataformas=("desktop",))
def desligar(ctx, unidade, qtd=None):
    n = para_numero(qtd) if qtd else 1
    if not n:
        ctx.dizer("desligar_invalido")
        return
    minutos = max(1, round(n * (60 if unidade == "hora" else 1)))
    ctx.acao("desligar", minutos=minutos)
    ctx.dizer("desligar_ok", minutos=minutos)


@habilidade(r"\bcancelar (?:o )?desligamento\b", descricao="Cancela desligamento",
            prioridade=5, plataformas=("desktop",))
def cancelar(ctx):
    ctx.acao("cancelar_desligamento")
    ctx.dizer("desligamento_cancelado")


@habilidade(_ABRIR, *_DESLIGAR, r"\bcancelar (?:o )?desligamento\b",
            descricao="Avisa que é só no desktop", prioridade=-2, plataformas=("web",))
def so_desktop(ctx, **_):
    ctx.dizer("so_desktop")


@habilidade(
    r"^(?:tchau|ate (?:mais|logo)|encerrar|sair|desligar|dormir|boa noite luna)$",
    r"\b(?:fechar|encerrar|desligar) (?:a )?(?:assistente|luna)\b",
    descricao="Encerra a assistente", prioridade=6,
)
def encerrar(ctx):
    ctx.dizer("tchau")
    ctx.acao("encerrar")
