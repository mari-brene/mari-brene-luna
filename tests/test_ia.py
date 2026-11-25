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


def test_lista_de_modelos(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("GEMINI_MODELO", " gemini-4-hydrogen , gemini-3.8-flash ,")
    conversa = criar_conversa()
    assert [c.modelo for c in conversa.clientes] == ["gemini-4-hydrogen", "gemini-3.8-flash"]


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
    assert conversa.responder("um", sessao).texto
    segundo = conversa.responder("dois", sessao)
    assert segundo.texto is None and segundo.fala == "ia_limite" and len(falso.chamadas) == 1


def test_503_tenta_de_novo_e_funciona(luna_ia, gemini):
    falso = gemini(RespostaFalsa(503, {"error": "overloaded"}), ok("Júpiter!"))
    r = luna_ia.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.texto == "Júpiter!" and len(falso.chamadas) == 2


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_indisponivel_sempre_vira_fala_de_sobrecarga(luna_ia, gemini, status):
    falso = gemini(*[RespostaFalsa(status, {"error": "x"})] * 2)
    sessao = Sessao("s" * 20)
    r = luna_ia.processar("qual o maior planeta", sessao)
    assert len(falso.chamadas) == 2  # 1 + 1 tentativa extra (poupa cota)
    assert r.habilidade is None
    assert "sobrecarregad" in r.texto.lower() or "503" in r.texto
    assert sessao.memoria_ia == []


@pytest.mark.parametrize("falha_primeiro", [503, 404, 429])
def test_passa_para_o_proximo_modelo(monkeypatch, gemini, falha_primeiro):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("GEMINI_MODELO", "modelo-a,modelo-b")
    luna = Luna(carregar_config(), plataforma="web")
    respostas = [RespostaFalsa(falha_primeiro, {"error": "x"})] * (2 if falha_primeiro == 503 else 1)
    falso = gemini(*respostas, ok("Do modelo B."))
    r = luna.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.texto == "Do modelo B."
    assert "modelo-a" in falso.chamadas[0]["url"] and "modelo-b" in falso.chamadas[-1]["url"]


def test_erro_de_chave_nao_tenta_outros_modelos(monkeypatch, gemini):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("GEMINI_MODELO", "modelo-a,modelo-b")
    luna = Luna(carregar_config(), plataforma="web")
    falso = gemini(RespostaFalsa(403, {"error": "forbidden"}))
    luna.processar("qual o maior planeta", Sessao("s" * 20))
    assert len(falso.chamadas) == 1


def test_log_mostra_a_mensagem_do_google(luna_ia, gemini, caplog):
    corpo = {"error": {"code": 503, "status": "UNAVAILABLE", "message": "The model is overloaded."}}
    gemini(*[RespostaFalsa(503, corpo)] * 2)
    luna_ia.processar("qual o maior planeta", Sessao("s" * 20))
    assert "UNAVAILABLE The model is overloaded." in caplog.text


# ------------------------------------------------------------ function calling
def chama(frase, texto=""):
    partes = ([{"text": texto}] if texto else []) + [
        {"functionCall": {"name": "executar_comando", "args": {"frase": frase}}, "thoughtSignature": "abc"}
    ]
    return RespostaFalsa(200, {"candidates": [{"content": {"role": "model", "parts": partes}}]})


def test_envia_a_ferramenta_e_os_exemplos_da_plataforma(luna_ia, gemini):
    falso = gemini(ok("Oi!"))
    luna_ia.processar("me fala algo", Sessao("s" * 20))
    corpo = falso.chamadas[0]["json"]
    [declaracao] = corpo["tools"][0]["functionDeclarations"]
    assert declaracao["name"] == "executar_comando" and declaracao["parameters"]["required"] == ["frase"]
    instrucoes = corpo["systemInstruction"]["parts"][0]["text"]
    assert "Timer de 10 minutos" in instrucoes and "Lembrar de pagar a internet" in instrucoes
    assert "Abrir Discord" not in instrucoes  # web não tem comandos de desktop


def test_ia_transforma_pedido_livre_em_comando(luna_ia, gemini):
    gemini(chama("lembrar de comprar pão depois do almoço"))
    sessao = Sessao("s" * 20)
    r = luna_ia.processar("lembra de comprar pão depois do almoço, por favor", sessao)
    assert r.habilidade == "lembretes.criar" and r.via_ia is True
    assert "comprar pão depois do almoço" in luna_ia.processar("ver lembretes", sessao).texto


def test_prefere_a_chamada_ao_texto(luna_ia, gemini):
    gemini(chama("que horas são", texto="Vou ver aqui!"))
    r = luna_ia.processar("sabe me dizer as horas?", Sessao("s" * 20))
    assert r.habilidade == "tempo.hora" and "Vou ver" not in r.texto


def test_contexto_e_amanha_depois_do_clima(luna_ia, gemini, api_falsa):
    from test_habilidades import _clima

    api_falsa({"wttr.in": _clima(28, 90)})
    falso = gemini(chama("clima amanhã em Curitiba"))
    sessao = Sessao("s" * 20)
    luna_ia.processar("clima em Curitiba", sessao)        # comando normal, sem IA
    assert not falso.chamadas
    r = luna_ia.processar("e amanhã?", sessao)             # IA usa a memória
    enviados = [c["parts"][0]["text"] for c in falso.chamadas[0]["json"]["contents"]]
    assert enviados[0] == "clima em Curitiba" and "Curitiba" in enviados[1] and enviados[-1] == "e amanhã?"
    assert r.habilidade == "clima.clima" and r.via_ia and "amanhã em curitiba" in r.texto.lower()


@pytest.mark.parametrize("perigoso", ["limpar lembretes", "apagar lembrete 1"])
def test_comandos_destrutivos_exigem_frase_explicita(luna_ia, gemini, perigoso):
    gemini(chama(perigoso))
    sessao = Sessao("s" * 20)
    luna_ia.processar("lembrar de não perder isso", sessao)
    r = luna_ia.processar("some com tudo aí", sessao)
    assert perigoso in r.texto and not r.via_ia
    assert "não perder isso" in luna_ia.processar("ver lembretes", sessao).texto


def test_desligar_pc_via_ia_bloqueado_no_desktop(monkeypatch, gemini):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    luna = Luna(carregar_config(), plataforma="desktop")
    gemini(chama("desligar o computador em 10 minutos"))
    r = luna.processar("apaga o pc daqui a pouco", Sessao("s" * 20))
    assert not r.acoes and "desligar o computador" in r.texto


def test_comando_sugerido_desconhecido_vira_nao_entendi(luna_ia, gemini):
    falso = gemini(chama("fazer café expresso duplo"))
    r = luna_ia.processar("faz um café pra mim", Sessao("s" * 20))
    assert r.habilidade is None and r.falas and len(falso.chamadas) == 1  # sem recursão na IA


def test_comando_via_ia_pode_perguntar(luna_ia, gemini):
    gemini(chama("criar lembrete"))
    sessao = Sessao("s" * 20)
    r = luna_ia.processar("quero anotar uma coisa", sessao)
    assert r.aguardando_resposta and r.via_ia
    luna_ia.processar("ligar pro dentista", sessao)
    assert "ligar pro dentista" in luna_ia.processar("ver lembretes", sessao).texto


def test_via_ia_chega_na_saida_da_api(monkeypatch, gemini):
    from luna.web.servico import ServicoLuna

    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    gemini(chama("tocar Queen"))
    saida = ServicoLuna().comando("quero ouvir aquela banda do Freddie Mercury")
    assert saida["via_ia"] is True and saida["acoes"][0]["tipo"] == "abrir_url"


def test_cota_esgotada_em_todos_os_modelos(monkeypatch, gemini):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("GEMINI_MODELO", "modelo-a,modelo-b")
    luna = Luna(carregar_config(), plataforma="web")
    falso = gemini(*[RespostaFalsa(429, {"error": {"status": "RESOURCE_EXHAUSTED"}})] * 2)
    r = luna.processar("qual o maior planeta", Sessao("s" * 20))
    assert len(falso.chamadas) == 2 and any(p in r.texto.lower() for p in ("cota", "rate limit"))


# ------------------------------------------------------------ Grok (formato OpenAI)
def grok_ok(texto=None, frase_comando=None):
    mensagem = {"role": "assistant", "content": texto}
    if frase_comando:
        mensagem["tool_calls"] = [{"id": "c1", "type": "function", "function": {
            "name": "executar_comando", "arguments": json.dumps({"frase": frase_comando})}}]
    return RespostaFalsa(200, {"choices": [{"message": mensagem}]})


class Roteador:
    """requests.post falso que responde conforme o provedor da URL."""

    def __init__(self, gemini=(), grok=()):
        self.filas = {"googleapis": list(gemini), "x.ai": list(grok)}
        self.chamadas = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        provedor = "x.ai" if "x.ai" in url else "googleapis"
        self.chamadas.append({"provedor": provedor, "url": url, "json": copy.deepcopy(json), "headers": headers})
        return self.filas[provedor].pop(0)


@pytest.fixture
def roteador(monkeypatch):
    def configurar(**filas):
        r = Roteador(**filas)
        monkeypatch.setattr("requests.post", r)
        return r
    return configurar


def test_so_grok_configurado(monkeypatch, roteador):
    monkeypatch.setenv("XAI_API_KEY", "xai-teste")
    rot = roteador(grok=[grok_ok("Júpiter, fácil.")])
    luna = Luna(carregar_config(), plataforma="web")
    r = luna.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.texto == "Júpiter, fácil." and r.habilidade == "ia.conversa"
    [chamada] = rot.chamadas
    assert chamada["url"] == "https://api.x.ai/v1/chat/completions"
    assert chamada["headers"]["Authorization"] == "Bearer xai-teste"
    corpo = chamada["json"]
    assert corpo["model"] == "grok-4-1-fast-reasoning"
    assert corpo["messages"][0]["role"] == "system" and "Luna" in corpo["messages"][0]["content"]
    assert corpo["messages"][-1] == {"role": "user", "content": "qual o maior planeta"}
    assert corpo["tools"][0]["type"] == "function" and corpo["tools"][0]["function"]["name"] == "executar_comando"


def test_grok_chama_ferramenta(monkeypatch, roteador):
    monkeypatch.setenv("XAI_API_KEY", "xai-teste")
    roteador(grok=[grok_ok(frase_comando="tocar Queen")])
    luna = Luna(carregar_config(), plataforma="web")
    r = luna.processar("quero ouvir aquela banda do Freddie Mercury", Sessao("s" * 20))
    assert r.via_ia and r.acoes[0].dados["url"].endswith("/search/Queen")


def test_grok_memoria_vira_assistant(monkeypatch, roteador):
    monkeypatch.setenv("XAI_API_KEY", "xai-teste")
    rot = roteador(grok=[grok_ok("Júpiter."), grok_ok("95 luas.")])
    luna = Luna(carregar_config(), plataforma="web")
    sessao = Sessao("s" * 20)
    luna.processar("qual o maior planeta", sessao)
    luna.processar("e quantas luas ele tem", sessao)
    papeis = [m["role"] for m in rot.chamadas[1]["json"]["messages"]]
    assert papeis == ["system", "user", "assistant", "user"]


def test_gemini_sem_cota_passa_para_o_grok(monkeypatch, roteador):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("XAI_API_KEY", "xai-teste")
    rot = roteador(gemini=[RespostaFalsa(429, {"error": {"status": "RESOURCE_EXHAUSTED"}})],
                   grok=[grok_ok("Grok assumiu.")])
    luna = Luna(carregar_config(), plataforma="web")
    r = luna.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.texto == "Grok assumiu."
    assert [c["provedor"] for c in rot.chamadas] == ["googleapis", "x.ai"]


def test_ordem_dos_provedores_configuravel(monkeypatch, roteador):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setenv("XAI_API_KEY", "xai-teste")
    monkeypatch.setenv("LUNA_IA_ORDEM", "grok,gemini")
    rot = roteador(grok=[grok_ok("Primeiro o Grok.")])
    luna = Luna(carregar_config(), plataforma="web")
    assert luna.processar("qual o maior planeta", Sessao("s" * 20)).texto == "Primeiro o Grok."
    assert [c["provedor"] for c in rot.chamadas] == ["x.ai"]


@pytest.mark.parametrize("status, fala", [(402, ("cota", "rate limit")), (429, ("cota", "rate limit")),
                                          (401, ("código", "404", "entendi", "dois segundos"))])
def test_grok_erros(monkeypatch, roteador, status, fala):
    monkeypatch.setenv("XAI_API_KEY", "xai-teste")
    roteador(grok=[RespostaFalsa(status, {"error": {"message": "x"}})])
    luna = Luna(carregar_config(), plataforma="web")
    r = luna.processar("qual o maior planeta", Sessao("s" * 20))
    assert r.habilidade is None and any(p in r.texto.lower() for p in fala), r.texto
