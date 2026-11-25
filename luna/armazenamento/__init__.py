"""
Onde os lembretes ficam guardados, escolhido por variável de ambiente:

    SUPABASE_URL + SUPABASE_SECRET_KEY definidas  ->  Supabase (produção)
    caso contrário                                ->  SQLite em dados/luna.db
                                                      (ou no caminho de LUNA_DB)
"""

import os

from ..core.contexto import DADOS
from .base import ErroArmazenamento, Lembrete, RepositorioLembretes
from .sqlite import LembretesSQLite
from .supabase import LembretesSupabase

__all__ = ["ErroArmazenamento", "Lembrete", "RepositorioLembretes", "repositorio_lembretes"]


def repositorio_lembretes() -> RepositorioLembretes:
    url = os.environ.get("SUPABASE_URL", "").strip()
    chave = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if url and chave:
        return LembretesSupabase(url, chave)  # fuso: luna/core/relogio.py
    return LembretesSQLite(os.environ.get("LUNA_DB") or os.path.join(DADOS, "luna.db"))
