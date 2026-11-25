"""
Repositórios de lembretes. O Supabase é simulado por um PostgREST falso em
memória, que interpreta os filtros (eq., order) e valida os headers.
"""

import json
from datetime import datetime, timezone

import pytest
import requests

from luna.armazenamento import ErroArmazenamento, repositorio_lembretes
from luna.armazenamento.sqlite import LembretesSQLite
from luna.armazenamento.supabase import LembretesSupabase

URL = "https://projeto.supabase.co"
CHAVE_NOVA = "sb_secret_abc123"
CHAVE_LEGADA = "eyJhbGciOiJIUzI1NiJ9.legada.assinatura"


class RespostaFalsa:
    def __init__(self, status: int, corpo=None):
        self.status_code = status
        self._corpo = corpo
        self.text = json.dumps(corpo) if corpo is not None else ""

    def json(self):
        return self._corpo


class PostgRESTFalso:
    """Imita o suficiente do PostgREST do Supabase para os testes."""

    def __init__(self, chave_valida: str):
        self.chave_valida = chave_valida
        self.linhas: list[dict] = []
        self.proximo_id = 1
        self.chamadas: list[dict] = []
        self.fora_do_ar = False

    def __call__(self, metodo, url, params=None, json=None, headers=None, timeout=None):
        self.chamadas.append({"metodo": metodo, "url": url, "params": params, "json": json, "headers": headers})
        if self.fora_do_ar:
            raise requests.ConnectionError("sem rede")
        assert url == f"{URL}/rest/v1/lembretes"
        assert timeout, "toda chamada precisa de timeout"
        if headers.get("apikey") != self.chave_valida:
            return RespostaFalsa(401, {"message": "Invalid API key"})
        auth = headers.get("Authorization")
        if auth and not auth.removeprefix("Bearer ").startswith("eyJ") and auth != f"Bearer {headers['apikey']}":
            return RespostaFalsa(401, {"message": "Invalid JWT"})

        filtros = {k: v.removeprefix("eq.") for k, v in (params or {}).items() if v.startswith("eq.")}

        def casa(linha):
            return all(str(linha[k]) == v for k, v in filtros.items())

        if metodo == "POST":
            self.linhas.append({
                "id": self.proximo_id, **json,
                "criado_em": "2026-11-24T23:48:10.123456+00:00",  # 20:48 em Brasília
            })
            self.proximo_id += 1
            return RespostaFalsa(201)
        if metodo == "GET":
            campos = params["select"].split(",")
            achadas = sorted((l for l in self.linhas if casa(l)), key=lambda l: l["id"])
            return RespostaFalsa(200, [{c: l[c] for c in campos} for l in achadas])
        if metodo == "DELETE":
            assert filtros, "DELETE sem filtro apagaria a tabela inteira"
            self.linhas = [l for l in self.linhas if not casa(l)]
            return RespostaFalsa(204)
        raise AssertionError(metodo)


@pytest.fixture
def supabase(monkeypatch):
    falso = PostgRESTFalso(CHAVE_NOVA)
    monkeypatch.setattr("requests.request", falso)
    monkeypatch.setenv("SUPABASE_URL", URL + "/")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", CHAVE_NOVA)
    return falso


# ----------------------------------------------------------------- escolha
def test_sem_variaveis_usa_sqlite(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    assert isinstance(repositorio_lembretes(), LembretesSQLite)


def test_com_variaveis_usa_supabase(supabase):
    assert isinstance(repositorio_lembretes(), LembretesSupabase)


def test_so_a_url_nao_basta(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    assert isinstance(repositorio_lembretes(), LembretesSQLite)


# ----------------------------------------------------------------- headers
def test_chave_nova_vai_so_no_apikey():
    repo = LembretesSupabase(URL, CHAVE_NOVA)
    assert repo.headers["apikey"] == CHAVE_NOVA and "Authorization" not in repo.headers


def test_chave_legada_vai_tambem_no_bearer():
    repo = LembretesSupabase(URL, CHAVE_LEGADA)
    assert repo.headers["Authorization"] == f"Bearer {CHAVE_LEGADA}"


# ------------------------------------------------- contrato (os dois bancos)
@pytest.fixture(params=["sqlite", "supabase"])
def repo(request, tmp_path, monkeypatch):
    if request.param == "sqlite":
        return LembretesSQLite(str(tmp_path / "x.db"))
    monkeypatch.setattr("requests.request", PostgRESTFalso(CHAVE_NOVA))
    return LembretesSupabase(URL, CHAVE_NOVA)


def test_contrato_do_repositorio(repo):
    repo.adicionar("ana", "comprar pão")
    repo.adicionar("bia", "segredo da bia")
    repo.adicionar("ana", "estudar regex")

    lista = repo.listar("ana")
    assert [l.texto for l in lista] == ["comprar pão", "estudar regex"]

    repo.remover("bia", lista[0].id)  # bia não apaga lembrete da ana
    assert len(repo.listar("ana")) == 2

    repo.remover("ana", lista[0].id)
    assert [l.texto for l in repo.listar("ana")] == ["estudar regex"]

    repo.limpar("ana")
    assert repo.listar("ana") == []
    assert [l.texto for l in repo.listar("bia")] == ["segredo da bia"]


# ------------------------------------------------------------- específicos
def test_data_vem_no_fuso_de_brasilia(supabase):
    repo = LembretesSupabase(URL, CHAVE_NOVA)
    repo.adicionar("ana", "x")
    assert repo.listar("ana")[0].criado_em == "24/11 20:48"


def test_usuario_com_caracteres_especiais_nao_vaza_filtro(supabase):
    repo = LembretesSupabase(URL, CHAVE_NOVA)
    repo.adicionar("ana", "da ana")
    assert repo.listar("ana&usuario=neq.x") == []


@pytest.mark.parametrize("problema", ["chave_errada", "fora_do_ar"])
def test_falhas_viram_erro_de_armazenamento(supabase, problema):
    if problema == "chave_errada":
        repo = LembretesSupabase(URL, "sb_secret_errada")
    else:
        supabase.fora_do_ar = True
        repo = LembretesSupabase(URL, CHAVE_NOVA)
    with pytest.raises(ErroArmazenamento):
        repo.listar("ana")


# ------------------------------------------------- pela Luna, de ponta a ponta
def test_luna_usa_o_supabase_quando_configurado(luna, sessao, supabase):
    luna.processar("lembrar de pagar a internet", sessao)
    r = luna.processar("ver lembretes", sessao)
    assert "pagar a internet" in r.texto and "24/11 20:48" in r.texto
    assert supabase.linhas[0]["usuario"] == sessao.id
    assert all("Authorization" not in c["headers"] for c in supabase.chamadas)


def test_luna_avisa_quando_o_banco_falha(luna, sessao, supabase):
    supabase.fora_do_ar = True
    r = luna.processar("ver lembretes", sessao)
    assert r.habilidade == "lembretes.listar"
    assert len(r.falas) == 1 and "lembrete" in r.texto.lower()


def test_pergunta_pendente_salva_no_supabase(luna, sessao, supabase):
    luna.processar("criar lembrete", sessao)
    luna.processar("revisar o PR", sessao)
    assert [l["texto"] for l in supabase.linhas] == ["revisar o PR"]


def test_relogio_iso_com_z(supabase):
    repo = LembretesSupabase(URL, CHAVE_NOVA)
    assert repo._formatar("2026-01-01T12:00:00Z") == "01/01 09:00"
    assert repo._formatar(datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()) == "31/12 21:00"
