"""IA de conversa com o Gemini simulado (nenhuma chamada real)."""

import copy
import json

import pytest
import requests

from luna.core.assistente import Luna
from luna.core.contexto import carregar_config
from luna.core.sessao import Sessao
from luna.ia import Conversa, criar_conversa
from luna.ia.gemini import ClienteGemini
from luna.ia.limites import LimitadorTaxa

CHAVE = "AIza-teste"


class RespostaFalsa:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo
        self.text = json.dumps(corpo)

    def json(self):
        return self._corpo


def ok(texto, pensamento=None):
    partes = ([{"text": pensamento, "thought": True}] if pensamento else []) + [{"text": texto}]
    return RespostaFalsa(200, {"candidates": [{"content": {"role": "model", "parts": partes}}]})


class GeminiFalso:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        # copia o corpo, como uma requisição HTTP real (o cliente pode alterar o dict depois)
        self.chamadas.append({"url": url, "json": copy.deepcopy(json), "headers": headers, "timeout": timeout})
        r = self.respostas.pop(0) if self.respostas else ok("resposta padrão")
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def gemini(monkeypatch):
    def configurar(*respostas):
        falso = GeminiFalso(*respostas)
        monkeypatch.setattr("requests.post", falso)
        return falso
    return configurar


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(ClienteGemini, "_dormir", staticmethod(lambda s: None))


@pytest.fixture
def luna_ia(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("GEMINI_MODELO", "gemini-teste-flash")
    return Luna(carregar_config(), plataforma="web")


# ------------------------------------------------------------ ativação
def test_sem_chave_continua_nao_entendi(luna, sessao, gemini):
    falso = gemini()
    r = luna.processar("qual o maior planeta", sessao)
    assert luna.ia is None and r.habilidade is None and not falso.chamadas


def test_com_chave_a_ia_e_criada(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    conversa = criar_conversa()
    assert conversa and conversa.cliente.modelo == "gemini-3.8-flash"


# ------------------------------------------------------------ requisição
def test_frase_desconhecida_vai_para_o_gemini(luna_ia, gemini):
    falso = gemini(ok("Júpiter, o grandalhão do sistema solar 🪐"))
    r = luna_ia.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.habilidade == "ia.conversa" and "Júpiter" in r.texto

    [chamada] = falso.chamadas
    assert chamada["url"].endswith("/models/gemini-teste-flash:generateContent")
    assert chamada["headers"]["x-goog-api-key"] == CHAVE
    assert chamada["timeout"]
    corpo = chamada["json"]
    assert "Luna" in corpo["systemInstruction"]["parts"][0]["text"]
    assert corpo["contents"] == [{"role": "user", "parts": [{"text": "qual o maior planeta"}]}]
    assert corpo["generationConfig"]["maxOutputTokens"] <= 500


def test_comandos_conhecidos_nao_gastam_ia(luna_ia, gemini):
    falso = gemini()
    r = luna_ia.processar("que horas são", Sessao("s" * 20))
    assert r.habilidade == "tempo.hora" and not falso.chamadas


def test_lembra_o_contexto_da_conversa(luna_ia, gemini):
    falso = gemini(ok("Júpiter."), ok("Tem 95 luas conhecidas."))
    sessao = Sessao("s" * 20)
    luna_ia.processar("qual o maior planeta", sessao)
    luna_ia.processar("e quantas luas ele tem", sessao)
    enviados = [c["parts"][0]["text"] for c in falso.chamadas[1]["json"]["contents"]]
    assert enviados == ["qual o maior planeta", "Júpiter.", "e quantas luas ele tem"]


def test_memoria_e_curta_e_por_sessao(luna_ia, gemini):
    gemini(*[ok(f"r{i}") for i in range(20)])
    a, b = Sessao("a" * 20), Sessao("b" * 20)
    for i in range(10):
        luna_ia.processar(f"pergunta aleatória {i}", a)
    assert len(a.memoria_ia) == 12 and a.memoria_ia[-1] == ("model", "r9")
    assert b.memoria_ia == []


def test_ignora_os_pensamentos_do_modelo(luna_ia, gemini):
    gemini(ok("Resposta final.", pensamento="raciocínio interno"))
    r = luna_ia.processar("me explica algo", Sessao("s" * 20))
    assert r.texto == "Resposta final."


def test_limpa_markdown_e_corta_textos_longos(luna_ia, gemini):
    longo = "**Olha só**: " + " ".join(["Frase de teste bem comprida aqui."] * 60)
    gemini(ok(longo))
    r = luna_ia.processar("fala bastante", Sessao("s" * 20))
    assert "*" not in r.texto and len(r.texto) <= 700 and r.texto.endswith(".")


# ------------------------------------------------------------ falhas
def test_cota_esgotada(luna_ia, gemini):
    gemini(RespostaFalsa(429, {"error": {"message": "quota"}}))
    r = luna_ia.processar("me conta algo", Sessao("s" * 20))
    assert r.habilidade is None
    assert any(p in r.texto.lower() for p in ("cota", "rate limit"))


@pytest.mark.parametrize("falha", [
    requests.ConnectionError("sem rede"),
    RespostaFalsa(403, {"error": "permission denied"}),
    RespostaFalsa(200, {"promptFeedback": {"blockReason": "SAFETY"}}),
    RespostaFalsa(200, {"candidates": [{"content": {"parts": [{"text": "  "}]}}]}),
])
def test_falhas_viram_nao_entendi_e_nao_sujam_a_memoria(luna_ia, gemini, falha):
    gemini(falha)
    sessao = Sessao("s" * 20)
    r = luna_ia.processar("pergunta qualquer", sessao)
    assert r.falas and r.habilidade is None and sessao.memoria_ia == []


def test_modelo_sem_thinking_tenta_de_novo_sem(luna_ia, gemini):
    falso = gemini(RespostaFalsa(400, {"error": "thinking not supported"}), ok("Funcionou."), ok("De novo."))
    sessao = Sessao("s" * 20)
    assert luna_ia.processar("oi tudo certo por ai", sessao).texto == "Funcionou."
    assert "thinkingConfig" in falso.chamadas[0]["json"]["generationConfig"]
    assert "thinkingConfig" not in falso.chamadas[1]["json"]["generationConfig"]
    luna_ia.processar("mais uma pergunta", sessao)
    assert "thinkingConfig" not in falso.chamadas[2]["json"]["generationConfig"]  # lembrou


# ------------------------------------------------------------ limites
class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_limite_por_sessao():
    relogio = Relogio()
    lim = LimitadorTaxa(por_sessao=3, janela_sessao=3600, global_por_minuto=100, relogio=relogio)
    assert [lim.permitir("a") for _ in range(4)] == [True, True, True, False]
    assert lim.permitir("b")  # outra sessão não é afetada
    relogio.t = 3601
    assert lim.permitir("a")  # janela passou


def test_limite_global_por_minuto():
    relogio = Relogio()
    lim = LimitadorTaxa(por_sessao=100, global_por_minuto=2, relogio=relogio)
    assert lim.permitir("a") and lim.permitir("b") and not lim.permitir("c")
    relogio.t = 61
    assert lim.permitir("c")


def test_limite_estourado_avisa_sem_chamar_o_gemini(gemini):
    falso = gemini()
    conversa = Conversa(ClienteGemini(CHAVE, "m"), LimitadorTaxa(por_sessao=1, global_por_minuto=100))
    sessao = Sessao("s" * 20)
    assert conversa.responder("um", sessao)[0]
    texto, fala = conversa.responder("dois", sessao)
    assert texto is None and fala == "ia_limite" and len(falso.chamadas) == 1


def test_503_tenta_de_novo_e_funciona(luna_ia, gemini):
    falso = gemini(RespostaFalsa(503, {"error": "overloaded"}), ok("Júpiter!"))
    r = luna_ia.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.texto == "Júpiter!" and len(falso.chamadas) == 2


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_indisponivel_sempre_vira_fala_de_sobrecarga(luna_ia, gemini, status):
    falso = gemini(*[RespostaFalsa(status, {"error": "x"})] * 3)
    sessao = Sessao("s" * 20)
    r = luna_ia.processar("qual o maior planeta", sessao)
    assert len(falso.chamadas) == 3  # 1 + 2 tentativas extras
    assert r.habilidade is None
    assert "sobrecarregad" in r.texto.lower() or "503" in r.texto
    assert sessao.memoria_ia == []
