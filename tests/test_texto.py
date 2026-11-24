import pytest

from luna.core.texto import em_reais, normalizar, normalizar_com_mapa, para_numero, trecho_original


@pytest.mark.parametrize("entrada, esperado", [
    ("Que horas são?", "que horas sao"),
    ("  Oi,   tudo   BEM!! ", "oi tudo bem"),
    ("Quanto é 2,5 euros?", "quanto e 2,5 euros"),
    ("timer de 1.5 horas.", "timer de 1.5 horas"),
    ("Pão, leite e ovos.", "pao leite e ovos"),
    ("", ""),
])
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


def test_mapa_recupera_texto_original():
    frase = "Lembrar de revisar o Currículo!"
    comando, mapa = normalizar_com_mapa(frase)
    inicio = comando.index("revisar")
    assert trecho_original(frase, mapa, inicio, len(comando)) == "revisar o Currículo"


@pytest.mark.parametrize("entrada, esperado", [
    ("5", 5), ("2,5", 2.5), ("1.5", 1.5), ("cinco", 5), ("meia", 0.5), ("dez", 10), ("banana", None),
])
def test_para_numero(entrada, esperado):
    assert para_numero(entrada) == esperado


@pytest.mark.parametrize("valor, esperado", [
    (5.0, "5 reais"), (5.5, "5 reais e 50 centavos"), (0.999, "1 reais"),
])
def test_em_reais(valor, esperado):
    assert em_reais(valor) == esperado
