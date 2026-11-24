"""Clima atual e de amanhã via wttr.in (sem chave de API), com comentário da Luna."""

import urllib.parse

import requests

from ..core.contexto import HEADERS, TIMEOUT
from ..core.personalidade import fala
from ..core.registro import habilidade


def _consultar(cidade: str) -> dict:
    return requests.get(
        f"https://wttr.in/{urllib.parse.quote(cidade)}",
        params={"format": "j1", "lang": "pt"}, headers=HEADERS, timeout=TIMEOUT,
    ).json()


def _descricao(bloco: dict) -> str:
    return (bloco.get("lang_pt") or bloco["weatherDesc"])[0]["value"].lower()


def _comentario(maxima: int, chuva: int) -> str:
    if chuva >= 60:
        return " " + fala("clima_chuva")
    if maxima >= 32:
        return " " + fala("clima_calor")
    if maxima <= 15:
        return " " + fala("clima_frio")
    return ""


@habilidade(
    r"\b(?:clima|tempo|previsao|temperatura)(?P<amanha> (?:de |para )?amanha)?(?: (?:em|de|para|no|na) (?P<cidade>.+))?$",
    r"\b(?:vai chover|esta (?:frio|calor))(?P<amanha> amanha)?(?: (?:em|no|na) (?P<cidade>.+))?",
    descricao="Clima de hoje ou amanhã", exemplo="Clima amanhã em Curitiba", livres=("cidade",),
)
def clima(ctx, cidade=None, amanha=None):
    cidade = cidade or ctx.config.get("cidade_padrao", "São Paulo")
    try:
        dados = _consultar(cidade)
        dia = dados["weather"][1 if amanha else 0]
        chuva = max(int(h["chanceofrain"]) for h in dia["hourly"])
        maxima = int(dia["maxtempC"])
        if amanha:
            texto = fala("clima_amanha", cidade=cidade, desc=_descricao(dia["hourly"][4]),
                         min=dia["mintempC"], max=maxima, chuva=chuva)
        else:
            atual = dados["current_condition"][0]
            texto = fala("clima_agora", cidade=cidade, temp=atual["temp_C"], desc=_descricao(atual),
                         min=dia["mintempC"], max=maxima)
    except (requests.RequestException, KeyError, IndexError, ValueError):
        ctx.dizer("clima_erro", cidade=cidade)
        return
    ctx.falar(texto + _comentario(maxima, chuva))
