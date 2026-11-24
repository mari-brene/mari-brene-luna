"""Cada frase deve cair na habilidade certa, com os argumentos certos."""

import pytest

from luna.core import registro
from luna.core.assistente import Luna  # noqa: F401  (importa e registra as habilidades)
from luna.core.registro import encontrar

import luna.habilidades  # noqa: F401,E402

CASOS = [
    ("Que horas são?", "tempo.hora", {}),
    ("que dia é hoje", "tempo.data", {}),
    ("timer de 5 minutos", "tempo.timer", {"qtd": "5", "unidade": "minuto"}),
    ("me avisa daqui a dez minutos", "tempo.timer", {"qtd": "dez", "unidade": "minuto"}),
    ("iniciar pomodoro", "tempo.pomodoro", {}),
    ("cancelar timer", "tempo.cancelar_timers", {}),
    ("pesquisar receita de bolo", "web.google", {"termo": "receita de bolo"}),
    ("Pesquisar lofi no YouTube", "web.youtube", {"termo": "lofi"}),
    ("Quem foi Santos Dumont?", "web.wikipedia", {"termo": "Santos Dumont"}),
    ("cotação do dólar e do bitcoin", "financas.cotacao", {}),
    ("quanto é 50 dólares em reais", "financas.converter", {"qtd": "50", "moeda": "dolares"}),
    ("clima", "clima.clima", {}),
    ("clima em São Paulo", "clima.clima", {"cidade": "São Paulo"}),
    ("vai chover amanhã em Curitiba", "clima.clima", {"amanha": "amanha", "cidade": "Curitiba"}),
    ("últimas notícias", "noticias.noticias", {}),
    ("notícias sobre Inteligência Artificial", "noticias.noticias", {"tema": "Inteligência Artificial"}),
    ("tocar Legião Urbana", "musica.tocar", {"musica": "Legião Urbana"}),
    ("toca Queen no YouTube", "musica.tocar", {"musica": "Queen", "yt": "no youtube"}),
    ("como se diz bom dia em francês", "tradutor.traduzir", {"frase": "bom dia", "idioma": "frances"}),
    ("traduzir para o inglês", "tradutor.traduzir", {"idioma": "ingles"}),
    ("lembrar de pagar a internet", "lembretes.criar", {"texto": "pagar a internet"}),
    ("criar novo lembrete", "lembretes.criar", {}),
    ("quais são os meus lembretes", "lembretes.listar", {}),
    ("apagar lembrete 2", "lembretes.apagar", {"num": "2"}),
    ("limpar lembretes", "lembretes.limpar", {}),
    ("abrir Discord", "sistema.abrir", {"alvo": "Discord"}),
    ("desligar o computador em meia hora", "sistema.desligar", {"qtd": "meia", "unidade": "hora"}),
    ("cancelar desligamento", "sistema.cancelar", {}),
    ("tchau", "sistema.encerrar", {}),
    ("quem é você", "conversa.apresentacao", {}),
    ("o que você sabe fazer", "conversa.ajuda", {}),
    ("Oi, tudo bem?", "conversa.saudacao", {}),
    ("qual o sentido da vida", "conversa.easter_egg", {}),
]


@pytest.mark.parametrize("frase, habilidade, args", CASOS, ids=[c[0] for c in CASOS])
def test_roteamento_desktop(frase, habilidade, args):
    hab, encontrados, _ = encontrar(frase, plataforma="desktop")
    assert hab is not None, f"nenhuma habilidade para {frase!r}"
    assert hab.nome == habilidade
    assert encontrados == args


@pytest.mark.parametrize("frase", ["fazer café", "blablabla", ""])
def test_frase_desconhecida(frase):
    hab, _, _ = encontrar(frase)
    assert hab is None


@pytest.mark.parametrize("frase", ["abrir Discord", "desligar o computador em 1 hora", "cancelar desligamento"])
def test_comandos_de_sistema_na_web_viram_aviso(frase):
    hab, _, _ = encontrar(frase, plataforma="web")
    assert hab.nome == "sistema.so_desktop"


def test_todas_as_habilidades_com_exemplo_casam_o_proprio_exemplo():
    """O exemplo mostrado no 'ajuda' tem que funcionar de verdade."""
    for hab in registro.HABILIDADES:
        if hab.exemplo:
            achada, _, _ = encontrar(hab.exemplo, plataforma="desktop")
            assert achada is hab, f"{hab.nome}: exemplo {hab.exemplo!r} caiu em {achada and achada.nome}"
