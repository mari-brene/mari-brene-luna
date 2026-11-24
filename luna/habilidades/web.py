"""Pesquisa no Google/YouTube e resumos da Wikipédia."""

import urllib.parse
import webbrowser

import requests

from ..core.contexto import HEADERS, TIMEOUT
from ..core.registro import habilidade


@habilidade(
    r"(?:pesquis[ae]r?|procurar?|buscar?) (?:por |sobre )?(?P<termo>.+?) no youtube$",
    descricao="Pesquisa no YouTube", exemplo="Pesquisar lofi no YouTube", prioridade=2, livres=("termo",),
)
def youtube(ctx, termo):
    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(termo)}")
    ctx.dizer("youtube", termo=termo)


@habilidade(
    r"(?:pesquis[ae]r?|procurar?|buscar?|googlar) (?:por |sobre )?(?P<termo>.+?)(?: no google)?$",
    descricao="Pesquisa no Google", exemplo="Pesquisar receita de bolo", livres=("termo",),
)
def google(ctx, termo):
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(termo)}")
    ctx.dizer("google", termo=termo)


@habilidade(
    r"^(?:o que (?:e|sao)|quem (?:e|foi|era)|me fale sobre) (?:o |a |os |as |um |uma )?(?P<termo>.+)$",
    descricao="Resumo da Wikipédia", exemplo="Quem foi Santos Dumont?", prioridade=-1, livres=("termo",),
)
def wikipedia(ctx, termo):
    try:
        busca = requests.get(
            "https://pt.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": termo, "limit": 1, "format": "json"},
            headers=HEADERS, timeout=TIMEOUT,
        ).json()
        if not busca[1]:
            ctx.dizer("wiki_vazio", termo=termo)
            return
        titulo = busca[1][0]
        resumo = requests.get(
            f"https://pt.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titulo)}",
            headers=HEADERS, timeout=TIMEOUT,
        ).json()["extract"]
    except (requests.RequestException, KeyError, ValueError, IndexError):
        ctx.dizer("sem_internet")
        return
    frases = resumo.split(". ")
    ctx.dizer("wiki_intro")
    ctx.falar(". ".join(frases[:2]).rstrip(".") + ".")
