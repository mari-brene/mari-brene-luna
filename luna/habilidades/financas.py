"""Cotações e conversão de moedas para real (AwesomeAPI)."""

import requests

from ..core.contexto import HEADERS, TIMEOUT
from ..core.registro import habilidade
from ..core.texto import em_reais, para_numero

MOEDAS = {
    "dolar": ("USD", "dólar"), "dolares": ("USD", "dólar"),
    "euro": ("EUR", "euro"), "euros": ("EUR", "euro"),
    "libra": ("GBP", "libra"), "libras": ("GBP", "libra"),
    "peso": ("ARS", "peso argentino"), "pesos": ("ARS", "peso argentino"),
    "iene": ("JPY", "iene"), "ienes": ("JPY", "iene"),
    "bitcoin": ("BTC", "bitcoin"), "bitcoins": ("BTC", "bitcoin"),
    "ethereum": ("ETH", "ethereum"),
}
_GRUPO = "|".join(sorted(MOEDAS, key=len, reverse=True))


def _cotar(codigos: list[str]) -> dict[str, float]:
    pares = ",".join(f"{c}-BRL" for c in dict.fromkeys(codigos))
    dados = requests.get(
        f"https://economia.awesomeapi.com.br/json/last/{pares}", headers=HEADERS, timeout=TIMEOUT
    ).json()
    return {c: float(dados[f"{c}BRL"]["bid"]) for c in codigos}


@habilidade(
    rf"quanto (?:e|sao|da) (?P<qtd>[\w,.]+) (?P<moeda>{_GRUPO})(?: em reais)?",
    descricao="Converte para reais", exemplo="Quanto é 50 dólares em reais?", prioridade=1,
)
def converter(ctx, qtd, moeda):
    n = para_numero(qtd)
    codigo, _ = MOEDAS[moeda]
    if n is None:
        ctx.dizer("valor_invalido")
        return
    try:
        cotacao = _cotar([codigo])[codigo]
    except (requests.RequestException, KeyError, ValueError):
        ctx.dizer("sem_internet")
        return
    ctx.dizer("conversao", qtd=qtd, moeda=moeda, valor=em_reais(n * cotacao))


@habilidade(r"\b(cotacao|quanto (?:esta|ta) o)\b", descricao="Cotação de moedas", exemplo="Cotação do euro")
def cotacao(ctx):
    comando = ctx.comando_atual
    pedidas = [MOEDAS[m] for m in MOEDAS if f" {m}" in f" {comando}"] or [MOEDAS["dolar"], MOEDAS["euro"]]
    pedidas = list(dict.fromkeys(pedidas))
    try:
        valores = _cotar([c for c, _ in pedidas])
    except (requests.RequestException, KeyError, ValueError):
        ctx.dizer("sem_internet")
        return
    for codigo, nome in pedidas:
        chave = "cotacao_sarcasmo_btc" if codigo == "BTC" else "cotacao"
        ctx.dizer(chave, moeda=nome, valor=em_reais(valores[codigo]))
