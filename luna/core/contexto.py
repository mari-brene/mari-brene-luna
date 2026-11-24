"""
Contexto que toda habilidade recebe como primeiro argumento.

Cada comando ganha um Contexto novo. As habilidades usam os métodos abaixo
para montar a Resposta, sem saber se estão no terminal ou na web.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Callable

from .personalidade import fala
from .resposta import Acao, Fala, Resposta
from .sessao import Pendente, Sessao

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
    sessao: Sessao
    plataforma: str = "desktop"   # "desktop" ou "web"
    sistema: str = ""             # "Windows" | "Linux" | "Darwin" (só faz sentido no desktop)
    comando_atual: str = ""       # comando normalizado em execução
    resposta: Resposta = field(default_factory=Resposta)

    @property
    def nome(self) -> str:
        return self.config["nome"]

    # ----------------------------------------------------------- falas
    def falar(self, texto: str, idioma: str = "pt") -> None:
        self.resposta.falas.append(Fala(texto, idioma))

    def dizer(self, chave: str, **valores) -> None:
        """Fala uma das variações da personalidade (ver core/personalidade.py)."""
        self.falar(fala(chave, **valores))

    # ----------------------------------------------------------- ações
    def acao(self, tipo: str, **dados) -> None:
        self.resposta.acoes.append(Acao(tipo, dados))

    def abrir_url(self, url: str) -> None:
        self.acao("abrir_url", url=url)

    def agendar(self, segundos: float, mensagem: str) -> None:
        self.acao("timer", segundos=segundos, mensagem=mensagem)

    # ----------------------------------------------------------- perguntas
    def perguntar(self, pergunta: str, continuar: Callable, idioma_escuta: str | None = None, **dados) -> None:
        """
        Faz uma pergunta e encerra a resposta atual. A próxima frase do usuário
        será entregue a `continuar(ctx, resposta=<frase>, **dados)`.
        """
        self.falar(pergunta)
        self.sessao.pendente = Pendente(continuar, dados)
        self.resposta.aguardando_resposta = True
        self.resposta.idioma_escuta = idioma_escuta
