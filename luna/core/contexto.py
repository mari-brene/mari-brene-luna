"""Contexto compartilhado que toda habilidade recebe como primeiro argumento."""

import json
import os
import platform
from dataclasses import dataclass

from .personalidade import fala

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DADOS = os.path.join(RAIZ, "dados")
HEADERS = {"User-Agent": "Mozilla/5.0 (Luna Assistente)"}
TIMEOUT = 10


def carregar_config() -> dict:
    with open(os.path.join(RAIZ, "config.json"), encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Contexto:
    config: dict
    io: object  # ModoTexto ou ModoVoz
    sistema: str = platform.system()
    rodando: bool = True
    comando_atual: str = ""  # comando normalizado em execução

    def falar(self, texto: str, idioma: str = "pt") -> None:
        self.io.falar(texto, idioma=idioma)

    def dizer(self, chave: str, **valores) -> None:
        """Fala uma das variações da personalidade (ver core/personalidade.py)."""
        self.falar(fala(chave, **valores))

    def ouvir(self, pergunta: str | None = None, **kwargs) -> str:
        return self.io.ouvir(pergunta, **kwargs)

    @property
    def nome(self) -> str:
        return self.config["nome"]
