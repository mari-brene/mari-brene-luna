"""Contrato dos repositórios de lembretes: as habilidades só conhecem esta interface."""

from dataclasses import dataclass
from typing import Protocol


class ErroArmazenamento(Exception):
    """Falha ao ler ou gravar (banco fora do ar, credencial errada...)."""


@dataclass(frozen=True)
class Lembrete:
    id: int
    texto: str
    criado_em: str  # já formatado para falar, ex.: "24/11 21:48"


class RepositorioLembretes(Protocol):
    def adicionar(self, usuario: str, texto: str) -> None: ...

    def listar(self, usuario: str) -> list[Lembrete]: ...

    def remover(self, usuario: str, lembrete_id: int) -> None: ...

    def limpar(self, usuario: str) -> None: ...
