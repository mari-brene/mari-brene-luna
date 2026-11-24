"""Casos de uso da web, sem servidor HTTP."""

import json

import pytest

from luna.web.servico import FraseInvalida, ServicoLuna


@pytest.fixture
def servico():
    return ServicoLuna()


def test_iniciar_devolve_sessao_e_saudacao(servico):
    saida = servico.iniciar()
    assert saida["nova_sessao"] and saida["sessao_id"]
    assert saida["falas"] and not saida["acoes"]


def test_retomar_sessao_existente(servico):
    sid = servico.iniciar()["sessao_id"]
    saida = servico.iniciar(sid)
    assert saida["sessao_id"] == sid and not saida["nova_sessao"]


def test_comando_sem_sessao_cria_uma(servico):
    saida = servico.comando("que horas são")
    assert saida["nova_sessao"] and saida["habilidade"] == "tempo.hora"


def test_pergunta_pendente_atravessa_requisicoes(servico):
    sid = servico.iniciar()["sessao_id"]
    pergunta = servico.comando("criar lembrete", sid)
    assert pergunta["aguardando_resposta"]
    servico.comando("estudar FastAPI", sid)
    assert "estudar FastAPI" in " ".join(f["texto"] for f in servico.comando("ver lembretes", sid)["falas"])


def test_usuarios_diferentes_nao_veem_lembretes_um_do_outro(servico):
    ana = servico.iniciar()["sessao_id"]
    bia = servico.iniciar()["sessao_id"]
    servico.comando("lembrar de segredo da Ana", ana)
    falas_bia = " ".join(f["texto"] for f in servico.comando("ver lembretes", bia)["falas"])
    assert "segredo" not in falas_bia


def test_acoes_de_desktop_nao_existem_na_web(servico):
    saida = servico.comando("desligar o computador em 10 minutos")
    assert saida["habilidade"] == "sistema.so_desktop" and not saida["acoes"]


def test_acao_de_url_vai_para_o_navegador(servico):
    saida = servico.comando("pesquisar regex no YouTube")
    assert saida["acoes"] == [{"tipo": "abrir_url", "dados": {"url": "https://www.youtube.com/results?search_query=regex"}}]


@pytest.mark.parametrize("frase", ["", "   ", "a" * 501])
def test_frase_invalida(servico, frase):
    with pytest.raises(FraseInvalida):
        servico.comando(frase)


def test_habilidades_web_tem_exemplo_e_nao_tem_desktop(servico):
    lista = servico.habilidades()
    nomes = {h["nome"] for h in lista}
    assert "tempo.timer" in nomes and "sistema.abrir" not in nomes
    assert all(h["exemplo"] for h in lista)


def test_saida_e_json(servico):
    json.dumps(servico.comando("iniciar pomodoro"))
