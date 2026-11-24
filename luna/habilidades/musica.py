"""Tocar música: abre a busca no Spotify ou no YouTube."""

import re
import urllib.parse
import webbrowser

from ..core.registro import habilidade


@habilidade(
    r"^(?:tocar?|toque|coloca|colocar|bota) (?P<musica>.+?)(?P<yt> no youtube)?$",
    descricao="Toca música no Spotify/YouTube", exemplo="Tocar Legião Urbana", livres=("musica",),
)
def tocar(ctx, musica, yt=None):
    musica = re.sub(r"\s+no spotify$", "", musica, flags=re.I)
    if yt:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(musica)}")
        ctx.dizer("musica_youtube", musica=musica)
    else:
        webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(musica)}")
        ctx.dizer("spotify", musica=musica)
