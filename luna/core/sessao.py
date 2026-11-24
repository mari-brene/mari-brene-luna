"""Estado de uma conversa entre um comando e o próximo."""

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Pendente:
    """Uma pergunta da Luna esperando resposta: a próxima frase vai para `continuar`."""
    continuar: Callable
    dados: dict = field(default_factory=dict)


@dataclass
class Sessao:
    id: str = "local"
    pendente: Pendente | None = None
    historico: list[tuple[str, str]] = field(default_factory=list)  # (frase, habilidade)

    def registrar(self, frase: str, habilidade: str | None) -> None:
        self.historico.append((frase, habilidade or "-"))
        del self.historico[:-50]  # guarda só as 50 últimas
