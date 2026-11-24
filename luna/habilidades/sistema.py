"""Abrir programas, agendar/cancelar desligamento e encerrar a assistente."""

import os
import subprocess

from ..core.registro import habilidade
from ..core.texto import normalizar, para_numero


@habilidade(r"^(?:abrir?|abra|inicia[r]?) (?:o |a )?(?P<alvo>.+)$",
            descricao="Abre programas", exemplo="Abrir Discord", prioridade=-2, livres=("alvo",))
def abrir(ctx, alvo):
    programas = ctx.config["programas"]
    nome = normalizar(alvo)
    chave = ctx.config.get("apelidos_programas", {}).get(nome, nome).replace(" ", "")
    comando = programas.get(chave, {}).get(ctx.sistema)
    if not comando:
        ctx.dizer("abrir_desconhecido", alvo=alvo)
        return
    try:
        subprocess.Popen(os.path.expandvars(comando), shell=True)
        ctx.dizer("abrir_ok", alvo=alvo)
    except OSError:
        ctx.dizer("abrir_erro", alvo=alvo)


@habilidade(
    r"\bdesligar? (?:o )?(?:computador|pc)(?: em| daqui a)? (?P<qtd>[\w,.]+)? ?(?P<unidade>minuto|hora)s?",
    r"\bdesligar? (?:o )?(?:computador|pc) em (?P<qtd>meia) (?P<unidade>hora)",
    descricao="Agenda desligamento", exemplo="Desligar o computador em 40 minutos", prioridade=4,
)
def desligar(ctx, unidade, qtd=None):
    n = para_numero(qtd) if qtd else 1
    if not n:
        ctx.dizer("desligar_invalido")
        return
    minutos = max(1, round(n * (60 if unidade == "hora" else 1)))
    cmd = f"shutdown /s /t {minutos * 60}" if ctx.sistema == "Windows" else f"shutdown -h +{minutos}"
    if os.system(cmd) == 0:
        ctx.dizer("desligar_ok", minutos=minutos)
    else:
        ctx.dizer("desligar_negado")


@habilidade(r"\bcancelar (?:o )?desligamento\b", descricao="Cancela desligamento", prioridade=5)
def cancelar(ctx):
    os.system("shutdown /a" if ctx.sistema == "Windows" else "shutdown -c")
    ctx.dizer("desligamento_cancelado")


@habilidade(
    r"^(?:tchau|ate (?:mais|logo)|encerrar|sair|desligar|dormir|boa noite luna)$",
    r"\b(?:fechar|encerrar|desligar) (?:a )?(?:assistente|luna)\b",
    descricao="Encerra a assistente", prioridade=6,
)
def encerrar(ctx):
    ctx.dizer("tchau")
    ctx.rodando = False
