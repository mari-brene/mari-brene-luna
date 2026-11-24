"""
Registro de habilidades.

Cada habilidade é uma função decorada com @habilidade, que recebe padrões
regex (aplicados ao comando normalizado: minúsculo, sem acento e sem
pontuação). Grupos nomeados do regex viram argumentos da função:

    @habilidade(r"clima (?:em|de) (?P<cidade>.+)", livres=("cidade",))
    def clima(ctx, cidade): ...

Grupos listados em `livres` chegam como o usuário falou (com acentos e
maiúsculas) — use para texto livre. Os demais chegam normalizados — use
para chaves de dicionário (moeda, idioma, unidade...).

`plataformas` restringe onde a habilidade existe ("desktop", "web").
Por padrão ela vale em todas.
"""

import re
from dataclasses import dataclass
from typing import Callable

from .texto import normalizar_com_mapa, trecho_original


@dataclass
class Habilidade:
    funcao: Callable
    padroes: list[re.Pattern]
    descricao: str
    exemplo: str
    prioridade: int
    livres: tuple[str, ...]
    plataformas: frozenset[str] | None
    ordem: int

    @property
    def nome(self) -> str:
        return f"{self.funcao.__module__.rsplit('.', 1)[-1]}.{self.funcao.__name__}"


HABILIDADES: list[Habilidade] = []


def habilidade(
    *padroes: str,
    descricao: str = "",
    exemplo: str = "",
    prioridade: int = 0,
    livres: tuple[str, ...] = (),
    plataformas: tuple[str, ...] | None = None,
):
    def decorador(funcao: Callable) -> Callable:
        HABILIDADES.append(
            Habilidade(
                funcao=funcao,
                padroes=[re.compile(p) for p in padroes],
                descricao=descricao,
                exemplo=exemplo,
                prioridade=prioridade,
                livres=livres,
                plataformas=frozenset(plataformas) if plataformas else None,
                ordem=len(HABILIDADES),
            )
        )
        return funcao
    return decorador


def disponiveis(plataforma: str | None = None) -> list[Habilidade]:
    return [h for h in HABILIDADES if plataforma is None or h.plataformas is None or plataforma in h.plataformas]


def encontrar(frase: str, plataforma: str | None = None):
    """
    Recebe a frase original. Devolve (habilidade, argumentos, comando_normalizado),
    com habilidade=None se nada casar.
    """
    comando, mapa = normalizar_com_mapa(frase)
    for hab in sorted(disponiveis(plataforma), key=lambda h: (-h.prioridade, h.ordem)):
        for padrao in hab.padroes:
            achou = padrao.search(comando)
            if not achou:
                continue
            args = {}
            for nome, valor in achou.groupdict().items():
                if not valor:
                    continue
                if nome in hab.livres:
                    args[nome] = trecho_original(frase, mapa, *achou.span(nome))
                else:
                    args[nome] = valor.strip()
            return hab, args, comando
    return None, {}, comando
