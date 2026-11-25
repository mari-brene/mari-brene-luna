"""Lembretes em SQLite local: o padrão no desktop e em desenvolvimento."""

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ..core.relogio import agora
from .base import ErroArmazenamento, Lembrete


class LembretesSQLite:
    def __init__(self, caminho: str):
        self.caminho = caminho

    @contextmanager
    def _conexao(self) -> Iterator[sqlite3.Connection]:
        """Abre, faz commit (ou rollback) e fecha. Cria/migra a tabela se preciso."""
        try:
            os.makedirs(os.path.dirname(self.caminho) or ".", exist_ok=True)
            con = sqlite3.connect(self.caminho)
        except (OSError, sqlite3.Error) as erro:
            raise ErroArmazenamento(str(erro)) from erro
        try:
            con.execute(
                "CREATE TABLE IF NOT EXISTS lembretes ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL, criado_em TEXT NOT NULL,"
                " usuario TEXT NOT NULL DEFAULT 'local')"
            )
            colunas = {linha[1] for linha in con.execute("PRAGMA table_info(lembretes)")}
            if "usuario" not in colunas:  # banco criado por versão antiga
                con.execute("ALTER TABLE lembretes ADD COLUMN usuario TEXT NOT NULL DEFAULT 'local'")
            con.execute("CREATE INDEX IF NOT EXISTS idx_lembretes_usuario ON lembretes (usuario)")
            with con:
                yield con
        except sqlite3.Error as erro:
            raise ErroArmazenamento(str(erro)) from erro
        finally:
            con.close()

    def adicionar(self, usuario: str, texto: str) -> None:
        with self._conexao() as con:
            con.execute(
                "INSERT INTO lembretes (texto, criado_em, usuario) VALUES (?, ?, ?)",
                (texto, agora().strftime("%d/%m %H:%M"), usuario),
            )

    def listar(self, usuario: str) -> list[Lembrete]:
        with self._conexao() as con:
            linhas = con.execute(
                "SELECT id, texto, criado_em FROM lembretes WHERE usuario = ? ORDER BY id", (usuario,)
            ).fetchall()
        return [Lembrete(*linha) for linha in linhas]

    def remover(self, usuario: str, lembrete_id: int) -> None:
        with self._conexao() as con:
            con.execute("DELETE FROM lembretes WHERE id = ? AND usuario = ?", (lembrete_id, usuario))

    def limpar(self, usuario: str) -> None:
        with self._conexao() as con:
            con.execute("DELETE FROM lembretes WHERE usuario = ?", (usuario,))
