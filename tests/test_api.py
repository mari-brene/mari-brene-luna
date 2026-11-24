"""Testes HTTP da API. Pulados se FastAPI/httpx não estiverem instalados (rodam na CI)."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from luna.web.api import criar_app  # noqa: E402


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv("LUNA_CORS_ORIGINS", "https://luna.exemplo.app")
    return TestClient(criar_app())


def test_saude(cliente):
    assert cliente.get("/api/saude").json() == {"status": "ok"}


def test_fluxo_completo(cliente):
    inicio = cliente.post("/api/sessoes")
    assert inicio.status_code == 200
    sid = inicio.json()["sessao_id"]

    r = cliente.post("/api/comando", json={"frase": "criar lembrete", "sessao_id": sid})
    assert r.status_code == 200 and r.json()["aguardando_resposta"] is True

    cliente.post("/api/comando", json={"frase": "testar a API", "sessao_id": sid})
    falas = cliente.post("/api/comando", json={"frase": "ver lembretes", "sessao_id": sid}).json()["falas"]
    assert any("testar a API" in f["texto"] for f in falas)


def test_iniciar_sem_corpo_e_com_corpo(cliente):
    sid = cliente.post("/api/sessoes").json()["sessao_id"]
    r = cliente.post("/api/sessoes", json={"sessao_id": sid})
    assert r.json()["sessao_id"] == sid and r.json()["nova_sessao"] is False


def test_acao_no_formato_documentado(cliente):
    acoes = cliente.post("/api/comando", json={"frase": "tocar Queen"}).json()["acoes"]
    assert acoes == [{"tipo": "abrir_url", "dados": {"url": "https://open.spotify.com/search/Queen"}}]


@pytest.mark.parametrize("corpo", [{}, {"frase": ""}, {"frase": "a" * 501}, {"frase": "   "}, {"frase": "oi", "sessao_id": "x" * 65}])
def test_entrada_invalida_devolve_422(cliente, corpo):
    assert cliente.post("/api/comando", json=corpo).status_code == 422


def test_habilidades(cliente):
    lista = cliente.get("/api/habilidades").json()
    assert lista and {"nome", "descricao", "exemplo"} <= set(lista[0])


def test_cors_libera_so_a_origem_configurada(cliente):
    ok = cliente.options("/api/comando", headers={"Origin": "https://luna.exemplo.app", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "https://luna.exemplo.app"
    bloqueado = cliente.options("/api/comando", headers={"Origin": "https://malicioso.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bloqueado.headers


def test_docs_openapi(cliente):
    esquema = cliente.get("/openapi.json").json()
    assert "/api/comando" in esquema["paths"]
