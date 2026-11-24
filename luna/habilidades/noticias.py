"""Manchetes do Google News (geral ou por tema), lidas com Beautiful Soup."""

import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from ..core.contexto import HEADERS, TIMEOUT
from ..core.registro import habilidade

RSS = "https://news.google.com/rss{caminho}?hl=pt-BR&gl=BR&ceid=BR:pt-419{extra}"


@habilidade(
    r"\bnoticias? (?:sobre|de) (?P<tema>.+)$",
    r"\b(?:ultimas )?noticias\b",
    descricao="Manchetes (geral ou por tema)", exemplo="Notícias sobre tecnologia", livres=("tema",),
)
def noticias(ctx, tema=None):
    if tema:
        url = RSS.format(caminho="/search", extra=f"&q={urllib.parse.quote(tema)}")
    else:
        url = RSS.format(caminho="", extra="")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            sopa = BeautifulSoup(resp.read(), "html.parser")
    except Exception:
        ctx.dizer("sem_internet")
        return
    itens = sopa.find_all("item")[:3]
    if not itens:
        ctx.dizer("noticias_vazio")
        return
    ctx.dizer("noticias_intro", tema=f" sobre {tema}" if tema else "")
    for item in itens:
        titulo, _, fonte = item.title.get_text().rpartition(" - ")
        ctx.falar(f"{titulo or fonte}{', segundo ' + fonte if titulo else ''}.")
