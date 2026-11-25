"""
Cliente para APIs no formato Chat Completions da OpenAI (Grok/xAI e afins),
sem SDK. Mesma interface do ClienteGemini: gerar(instrucoes, conversa,
ferramentas) -> RespostaModelo.
"""

import json
import logging
import time

import requests

from .gemini import ErroIA, RespostaModelo

log = logging.getLogger("luna.ia")

TIMEOUT = 20
TEMPORARIOS = {500, 502, 503, 504}


class ClienteOpenAICompat:
    def __init__(self, chave: str, modelo: str, base_url: str, provedor: str, max_tokens: int = 400):
        self.chave = chave
        self.modelo = modelo
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.provedor = provedor
        self.max_tokens = max_tokens

    def __repr__(self) -> str:
        return f"{self.provedor}:{self.modelo}"

    def gerar(self, instrucoes: str, conversa: list[tuple[str, str]],
              ferramentas: list[dict] | None = None) -> RespostaModelo:
        mensagens = [{"role": "system", "content": instrucoes}] + [
            {"role": "assistant" if papel == "model" else "user", "content": texto} for papel, texto in conversa
        ]
        corpo: dict = {
            "model": self.modelo,
            "messages": mensagens,
            "max_tokens": self.max_tokens,
            "temperature": 0.9,
        }
        if ferramentas:
            corpo["tools"] = [{"type": "function", "function": f} for f in ferramentas]

        resposta = self._post(corpo)
        if resposta.status_code in TEMPORARIOS:  # 1 nova tentativa só (cada chamada custa)
            log.warning("%s respondeu %s (%s); tentando de novo", self, resposta.status_code, self._motivo(resposta))
            self._dormir(1.5)
            resposta = self._post(corpo)

        if resposta.status_code in (401, 403):
            raise ErroIA(f"{self.provedor}: chave recusada ({resposta.status_code}): {self._motivo(resposta)}")
        if resposta.status_code == 402 or resposta.status_code == 429:
            raise ErroIA(f"{self.provedor}: sem cota/créditos ({resposta.status_code}): {self._motivo(resposta)}",
                         cota_esgotada=True)
        if resposta.status_code in TEMPORARIOS:
            raise ErroIA(f"{self.provedor} indisponível ({resposta.status_code}): {self._motivo(resposta)}",
                         temporario=True)
        if resposta.status_code == 404:
            raise ErroIA(f"{self.provedor}: modelo {self.modelo} não encontrado (404)", modelo_inexistente=True)
        if resposta.status_code >= 400:
            raise ErroIA(f"{self.provedor} respondeu {resposta.status_code}: {self._motivo(resposta)}")

        try:
            mensagem = resposta.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as erro:
            raise ErroIA(f"{self.provedor}: resposta em formato inesperado") from erro

        chamada = None
        for tool_call in mensagem.get("tool_calls") or []:
            funcao = tool_call.get("function") or {}
            if funcao.get("name"):
                try:
                    argumentos = json.loads(funcao.get("arguments") or "{}")
                except ValueError:
                    argumentos = {}
                chamada = (funcao["name"], argumentos if isinstance(argumentos, dict) else {})
                break
        texto = (mensagem.get("content") or "").strip()
        if not texto and not chamada:
            raise ErroIA(f"{self.provedor} devolveu resposta vazia")
        return RespostaModelo(texto=texto, chamada=chamada)

    @staticmethod
    def _motivo(resposta: requests.Response) -> str:
        try:
            erro = resposta.json().get("error")
            if isinstance(erro, dict):
                return str(erro.get("message") or erro)[:300]
            if erro:
                return str(erro)[:300]
        except Exception:
            pass
        return resposta.text[:300]

    @staticmethod
    def _dormir(segundos: float) -> None:
        time.sleep(segundos)

    def _post(self, corpo: dict) -> requests.Response:
        try:
            return requests.post(
                self.url,
                json=corpo,
                headers={"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"},
                timeout=TIMEOUT,
            )
        except requests.RequestException as erro:
            raise ErroIA(f"{self.provedor} inacessível: {erro}") from erro
