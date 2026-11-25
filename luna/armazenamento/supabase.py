"""
Lembretes no Supabase, via API REST (PostgREST), sem SDK.

Usa a chave *secret* do projeto (sb_secret_...), que só existe no backend.
Chaves novas vão APENAS no header `apikey`: mandá-las também em
`Authorization: Bearer` faz o Supabase rejeitar com "Invalid JWT".
A chave legada service_role (um JWT, começa com "eyJ") ainda é aceita e
vai nos dois headers.

A tabela fica com RLS ligado e sem policies: só o backend (chave secret)
consegue ler/gravar. Ver supabase/lembretes.sql.
"""

from datetime import datetime, timedelta, timezone

import requests

from .base import ErroArmazenamento, Lembrete

TIMEOUT = 10


def _fuso(nome: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome)
    except Exception:  # Windows sem o pacote tzdata, nome inválido...
        return timezone(timedelta(hours=-3), "BRT")


class LembretesSupabase:
    def __init__(self, url: str, chave: str, fuso: str = "America/Sao_Paulo", tabela: str = "lembretes"):
        self.endpoint = f"{url.rstrip('/')}/rest/v1/{tabela}"
        self.fuso = _fuso(fuso)
        self.headers = {"apikey": chave, "Content-Type": "application/json"}
        if chave.startswith("eyJ"):  # chave legada (JWT)
            self.headers["Authorization"] = f"Bearer {chave}"

    def _requisitar(self, metodo: str, params: dict | None = None, json: dict | None = None,
                    prefer: str | None = None) -> requests.Response:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            resposta = requests.request(
                metodo, self.endpoint, params=params, json=json, headers=headers, timeout=TIMEOUT
            )
        except requests.RequestException as erro:
            raise ErroArmazenamento(f"Supabase inacessível: {erro}") from erro
        if resposta.status_code >= 400:
            raise ErroArmazenamento(f"Supabase respondeu {resposta.status_code}: {resposta.text[:200]}")
        return resposta

    def _formatar(self, iso: str) -> str:
        try:
            momento = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            return iso
        return momento.astimezone(self.fuso).strftime("%d/%m %H:%M")

    def adicionar(self, usuario: str, texto: str) -> None:
        self._requisitar("POST", json={"usuario": usuario, "texto": texto}, prefer="return=minimal")

    def listar(self, usuario: str) -> list[Lembrete]:
        resposta = self._requisitar(
            "GET",
            params={"select": "id,texto,criado_em", "usuario": f"eq.{usuario}", "order": "id.asc"},
        )
        return [Lembrete(l["id"], l["texto"], self._formatar(l["criado_em"])) for l in resposta.json()]

    def remover(self, usuario: str, lembrete_id: int) -> None:
        self._requisitar("DELETE", params={"id": f"eq.{lembrete_id}", "usuario": f"eq.{usuario}"})

    def limpar(self, usuario: str) -> None:
        self._requisitar("DELETE", params={"usuario": f"eq.{usuario}"})
