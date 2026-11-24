"""Utilitários de texto: normalização e números por extenso."""

import re
import unicodedata

_NUMEROS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "quinze": 15, "vinte": 20, "trinta": 30, "quarenta": 40, "quarenta e cinco": 45,
    "cinquenta": 50, "sessenta": 60, "cem": 100,
}


def normalizar_com_mapa(texto: str) -> tuple[str, list[int]]:
    """
    Minúsculas, sem acentos, sem pontuação e com espaços simples.
    Também devolve `mapa`, onde mapa[i] é a posição no texto original do
    caractere i do texto normalizado — assim um trecho casado pelo regex
    pode ser recuperado com acentos e maiúsculas.
    """
    saida: list[str] = []
    mapa: list[int] = []
    for i, c in enumerate(texto):
        base = "".join(x for x in unicodedata.normalize("NFKD", c.lower()) if not unicodedata.combining(x))
        entre_digitos = 0 < i < len(texto) - 1 and texto[i - 1].isdigit() and texto[i + 1].isdigit()
        if len(base) != 1 or not (base.isalnum() or base == "_" or (base in ".," and entre_digitos)):
            base = " "
        if base == " " and (not saida or saida[-1] == " "):
            continue  # colapsa espaços e remove os do início
        saida.append(base)
        mapa.append(i)
    while saida and saida[-1] == " ":
        saida.pop()
        mapa.pop()
    return "".join(saida), mapa


def normalizar(texto: str) -> str:
    return normalizar_com_mapa(texto)[0]


def trecho_original(original: str, mapa: list[int], inicio: int, fim: int) -> str:
    if inicio >= fim:
        return ""
    return original[mapa[inicio]: mapa[fim - 1] + 1].strip(" ,.?!")


def para_numero(texto: str) -> float | None:
    """'5', '2,5', 'cinco', 'meia' -> número. None se não reconhecer."""
    texto = texto.strip()
    if texto in ("meia", "meio"):
        return 0.5
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return _NUMEROS.get(texto)


def em_reais(valor: float) -> str:
    reais, centavos = int(valor), round((valor - int(valor)) * 100)
    if centavos == 100:
        reais, centavos = reais + 1, 0
    return f"{reais} reais" + (f" e {centavos} centavos" if centavos else "")
