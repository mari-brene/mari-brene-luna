import pytest

from luna.core.assistente import Luna
from luna.core.contexto import carregar_config
from luna.core.sessao import Sessao


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Cada teste usa um SQLite próprio: nunca o dados/luna.db nem um Supabase de verdade."""
    monkeypatch.setenv("LUNA_DB", str(tmp_path / "luna_teste.db"))
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    for variavel in ("XAI_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY", "MISTRAL_API_KEY", "OPENROUTER_API_KEY",
                     "LUNA_IA_ORDEM"):
        monkeypatch.delenv(variavel, raising=False)


@pytest.fixture
def luna():
    return Luna(carregar_config(), plataforma="desktop")


@pytest.fixture
def luna_web():
    return Luna(carregar_config(), plataforma="web")


@pytest.fixture
def sessao():
    return Sessao()


class RespostaFalsa:
    def __init__(self, dados):
        self._dados = dados

    def json(self):
        return self._dados


@pytest.fixture
def api_falsa(monkeypatch):
    """
    Substitui requests.get: api_falsa({"trecho-da-url": {...json...}}).
    Testes nunca acessam a internet.
    """
    def configurar(rotas: dict):
        def get(url, *args, **kwargs):
            for trecho, dados in rotas.items():
                if trecho in url:
                    return RespostaFalsa(dados)
            raise AssertionError(f"URL inesperada no teste: {url}")
        monkeypatch.setattr("requests.get", get)
    return configurar
