"""Comportamento das habilidades: falas, ações e perguntas. Sem internet e sem efeitos no sistema."""

import pytest


def acoes(resposta, tipo):
    return [a.dados for a in resposta.acoes if a.tipo == tipo]


# ------------------------------------------------------------------ tempo
def test_hora_responde_com_horario(luna, sessao):
    r = luna.processar("que horas são", sessao)
    assert r.habilidade == "tempo.hora"
    assert "h" in r.texto and not r.acoes


def test_timer_gera_acao_com_segundos(luna, sessao):
    r = luna.processar("timer de 10 minutos", sessao)
    [timer] = acoes(r, "timer")
    assert timer["segundos"] == 600
    assert "10 minutos" in timer["mensagem"]


def test_pomodoro_agenda_foco_e_pausa(luna, sessao):
    r = luna.processar("iniciar pomodoro", sessao)
    foco, volta = acoes(r, "timer")
    assert foco["segundos"] == 25 * 60
    assert volta["segundos"] == 30 * 60


def test_timer_invalido_nao_agenda(luna, sessao):
    r = luna.processar("timer de banana minutos", sessao)
    assert not r.acoes


# -------------------------------------------------------------- web/música
def test_pesquisa_google_abre_url(luna, sessao):
    r = luna.processar("pesquisar água de coco", sessao)
    [url] = acoes(r, "abrir_url")
    assert url["url"].startswith("https://www.google.com/search?q=")
    assert "%C3%A1gua" in url["url"]  # acento preservado e codificado


def test_tocar_no_spotify(luna, sessao):
    r = luna.processar("tocar Legião Urbana no Spotify", sessao)
    [url] = acoes(r, "abrir_url")
    assert url["url"] == "https://open.spotify.com/search/Legi%C3%A3o%20Urbana"


def test_wikipedia(luna, sessao, api_falsa):
    api_falsa({
        "w/api.php": ["santos dumont", ["Santos Dumont"], [], []],
        "page/summary": {"extract": "Alberto Santos Dumont foi um aeronauta. Nasceu em Minas. Outra frase."},
    })
    r = luna.processar("quem foi Santos Dumont", sessao)
    assert "aeronauta" in r.texto and "Outra frase" not in r.texto


# --------------------------------------------------------------- finanças
def test_conversao_de_moeda(luna, sessao, api_falsa):
    api_falsa({"awesomeapi": {"USDBRL": {"bid": "5.00"}}})
    r = luna.processar("quanto é 10 dólares em reais", sessao)
    assert "50 reais" in r.texto


def test_cotacao_padrao_dolar_e_euro(luna, sessao, api_falsa):
    api_falsa({"awesomeapi": {"USDBRL": {"bid": "5.1"}, "EURBRL": {"bid": "6.2"}}})
    r = luna.processar("cotação", sessao)
    assert "5 reais e 10 centavos" in r.texto and "6 reais e 20 centavos" in r.texto


def test_api_fora_do_ar_nao_quebra(luna, sessao, monkeypatch):
    import requests

    def falha(*a, **k):
        raise requests.ConnectionError("sem rede")
    monkeypatch.setattr("requests.get", falha)
    r = luna.processar("cotação do euro", sessao)
    assert r.falas and r.habilidade == "financas.cotacao"


# ------------------------------------------------------------------ clima
def _clima(maxima, chuva):
    hora = {"chanceofrain": str(chuva), "weatherDesc": [{"value": "Sunny"}], "lang_pt": [{"value": "Ensolarado"}]}
    dia = {"mintempC": "18", "maxtempC": str(maxima), "hourly": [hora] * 8}
    return {
        "current_condition": [{"temp_C": "25", "FeelsLikeC": "26", **hora}],
        "weather": [dia, dia],
    }


def test_clima_usa_cidade_padrao(luna, sessao, api_falsa):
    api_falsa({"wttr.in/Joinville": _clima(28, 10)})
    r = luna.processar("clima", sessao)
    assert "Joinville" in r.texto and "25 graus" in r.texto


def test_clima_de_amanha_com_chuva_comenta(luna, sessao, api_falsa):
    api_falsa({"wttr.in": _clima(28, 90)})
    r = luna.processar("vai chover amanhã em Curitiba", sessao)
    assert "Curitiba" in r.texto and "90%" in r.texto and "☔" in r.texto


# -------------------------------------------------------------- lembretes
def test_ciclo_completo_de_lembretes(luna, sessao):
    luna.processar("lembrar de revisar o currículo", sessao)
    luna.processar("anota que a reunião é às 15h", sessao)
    r = luna.processar("ver lembretes", sessao)
    assert "revisar o currículo" in r.texto and "a reunião é às 15h" in r.texto

    luna.processar("apagar lembrete 1", sessao)
    r = luna.processar("ver lembretes", sessao)
    assert "currículo" not in r.texto and "reunião" in r.texto

    luna.processar("limpar lembretes", sessao)
    r = luna.processar("ver lembretes", sessao)
    assert "1." not in r.texto


def test_apagar_lembrete_inexistente(luna, sessao):
    r = luna.processar("apagar lembrete 7", sessao)
    assert r.habilidade == "lembretes.apagar" and r.falas


# --------------------------------------------------- perguntas com sessão
def test_lembrete_sem_texto_pergunta_e_salva_a_resposta(luna, sessao):
    r = luna.processar("criar novo lembrete", sessao)
    assert r.aguardando_resposta and sessao.pendente

    r = luna.processar("comprar pão", sessao)
    assert not r.aguardando_resposta and sessao.pendente is None
    assert "comprar pão" in luna.processar("ver lembretes", sessao).texto


@pytest.mark.parametrize("desistencia", ["deixa pra lá", "cancelar", "esquece"])
def test_desistir_da_pergunta(luna, sessao, desistencia):
    luna.processar("criar lembrete", sessao)
    luna.processar(desistencia, sessao)
    assert sessao.pendente is None
    assert "1." not in luna.processar("ver lembretes", sessao).texto


def test_traduzir_para_portugues_escuta_em_ingles(luna, sessao):
    r = luna.processar("traduzir para o português", sessao)
    assert r.aguardando_resposta and r.idioma_escuta == "en-US"


def test_sessoes_sao_independentes(luna):
    from luna.core.sessao import Sessao
    a, b = Sessao("a"), Sessao("b")
    luna.processar("criar lembrete", a)
    r = luna.processar("que horas são", b)
    assert r.habilidade == "tempo.hora" and a.pendente and not b.pendente


# ---------------------------------------------------------------- sistema
def test_abrir_programa_conhecido_gera_acao(luna, sessao):
    r = luna.processar("abrir VS Code", sessao)
    [prog] = acoes(r, "abrir_programa")
    assert prog["nome"] == "VS Code"


def test_abrir_programa_desconhecido_nao_gera_acao(luna, sessao):
    r = luna.processar("abrir Photoshop", sessao)
    assert not r.acoes and "Photoshop" in r.texto


def test_desligar_calcula_minutos(luna, sessao):
    r = luna.processar("desligar o computador em meia hora", sessao)
    assert acoes(r, "desligar") == [{"minutos": 30}]


def test_web_nao_executa_comandos_de_sistema(luna_web, sessao):
    r = luna_web.processar("desligar o computador em 1 hora", sessao)
    assert not r.acoes and r.habilidade == "sistema.so_desktop"


def test_encerrar_gera_acao(luna, sessao):
    assert luna.processar("tchau", sessao).tem_acao("encerrar")


# ---------------------------------------------------------------- conversa
def test_ajuda_lista_so_o_que_existe_na_plataforma(luna, luna_web, sessao):
    desktop = luna.processar("ajuda", sessao).texto
    web = luna_web.processar("ajuda", sessao).texto
    assert "Abrir Discord" in desktop and "Abrir Discord" not in web


def test_nao_entendi(luna, sessao):
    r = luna.processar("fazer café", sessao)
    assert r.habilidade is None and r.falas


def test_erro_em_habilidade_vira_fala_amigavel(luna, sessao, monkeypatch):
    from luna.core import registro
    hab = next(h for h in registro.HABILIDADES if h.nome == "tempo.hora")

    def explode(ctx):
        raise RuntimeError("boom")
    monkeypatch.setattr(hab, "funcao", explode)
    r = luna.processar("que horas são", sessao)
    assert r.falas and not r.acoes


def test_resposta_serializa_para_json(luna, sessao):
    import json
    r = luna.processar("tocar Queen", sessao)
    dados = json.loads(json.dumps(r.para_dict()))
    assert dados["acoes"][0]["tipo"] == "abrir_url"
