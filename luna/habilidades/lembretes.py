"""Lembretes e anotações persistidos em SQLite."""

import os
import sqlite3
from datetime import datetime

from ..core.contexto import DADOS
from ..core.personalidade import fala
from ..core.registro import habilidade
from ..core.texto import para_numero

BANCO = os.path.join(DADOS, "luna.db")


def _conexao() -> sqlite3.Connection:
    os.makedirs(DADOS, exist_ok=True)
    con = sqlite3.connect(BANCO)
    con.execute(
        "CREATE TABLE IF NOT EXISTS lembretes ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL, criado_em TEXT NOT NULL)"
    )
    return con


def _listar(con) -> list[tuple[int, str, str]]:
    return con.execute("SELECT id, texto, criado_em FROM lembretes ORDER BY id").fetchall()


@habilidade(
    r"^(?:me )?lembr(?:e|ar)(?:-me)? de (?P<texto>.+)$",
    r"^(?:anot[ae]r?|anota ai) (?:que )?(?P<texto>.+)$",
    r"\b(?:criar|novo) (?:um )?lembrete\b(?: (?:de|para|que) (?P<texto>.+))?",
    descricao="Cria lembrete", exemplo="Lembrar de pagar a internet", livres=("texto",),
)
def criar(ctx, texto=None):
    texto = texto or ctx.ouvir(fala("lembrete_pergunta"), tempo_limite=8)
    if not texto:
        ctx.dizer("frase_vazia")
        return
    with _conexao() as con:
        con.execute(
            "INSERT INTO lembretes (texto, criado_em) VALUES (?, ?)",
            (texto, datetime.now().strftime("%d/%m %H:%M")),
        )
    ctx.dizer("lembrete_ok", texto=texto)


@habilidade(
    r"\b(?:apagar|excluir|remover|concluir) (?:o )?lembrete (?:numero )?(?P<num>\w+)\b",
    descricao="Apaga um lembrete", exemplo="Apagar lembrete 2", prioridade=3,
)
def apagar(ctx, num):
    n = para_numero(num)
    with _conexao() as con:
        lista = _listar(con)
        if not n or not 1 <= n <= len(lista):
            ctx.dizer("lembrete_inexistente")
            return
        id_, texto, _ = lista[int(n) - 1]
        con.execute("DELETE FROM lembretes WHERE id = ?", (id_,))
    ctx.dizer("lembrete_removido", texto=texto)


@habilidade(
    r"\b(?:apagar|limpar|excluir) (?:todos )?(?:os )?lembretes\b",
    descricao="Apaga todos os lembretes", prioridade=2,
)
def limpar(ctx):
    with _conexao() as con:
        con.execute("DELETE FROM lembretes")
    ctx.dizer("lembretes_limpos")


@habilidade(
    r"\b(?:ver|visualizar|listar|ler|quais (?:sao )?(?:os )?(?:meus )?)\s?(?:meus )?(?:lembretes|anotacoes)\b",
    r"^(?:meus )?lembretes$",
    descricao="Lista lembretes", exemplo="Ver lembretes",
)
def listar(ctx):
    with _conexao() as con:
        lista = _listar(con)
    if not lista:
        ctx.dizer("lembrete_vazio")
        return
    ctx.dizer("lembrete_lista", n=len(lista), s="s" if len(lista) > 1 else "")
    for i, (_, texto, quando) in enumerate(lista, 1):
        ctx.falar(f"{i}. {texto} (anotado em {quando})")
