"""
Relógio da Luna, sempre no fuso do usuário, nunca no do servidor.

Servidores como o Render rodam em UTC: um datetime.now() puro lá devolve a
hora de Londres. Tudo que mostra hora ou data deve usar agora() daqui.

Fuso: variável LUNA_FUSO > "fuso_horario" do config.json > America/Sao_Paulo.
"""

import os
from datetime import datetime, timedelta, timezone, tzinfo
from functools import lru_cache

PADRAO = "America/Sao_Paulo"


@lru_cache(maxsize=8)
def fuso(nome: str | None = None) -> tzinfo:
    nome = nome or os.environ.get("LUNA_FUSO") or _fuso_do_config() or PADRAO
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome)
    except Exception:  # Windows sem tzdata, nome inválido...
        return timezone(timedelta(hours=-3), "BRT")


def _fuso_do_config() -> str | None:
    try:
        from .contexto import carregar_config

        return carregar_config().get("fuso_horario")
    except Exception:
        return None


def agora() -> datetime:
    """Data e hora atuais no fuso da Luna (com tzinfo)."""
    return datetime.now(fuso())
