"""
Cliente mínimo da API do Gemini (REST, generateContent), sem SDK.

A chave vai no header `x-goog-api-key`. O modelo é configurável porque os
nomes mudam com frequência (GEMINI_MODELO).
"""

import logging

import requests

log = logging.getLogger("luna.ia")

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
TIMEOUT = 20


class ErroIA(Exception):
    def __init__(self, mensagem: str, cota_esgotada: bool = False):
        super().__init__(mensagem)
        self.cota_esgotada = cota_esgotada


class ClienteGemini:
    def __init__(self, chave: str, modelo: str, max_tokens: int = 400):
        self.chave = chave
        self.modelo = modelo
        self.max_tokens = max_tokens
        self._usar_thinking = True  # desliga sozinho se o modelo não aceitar

    def gerar(self, instrucoes: str, conversa: list[tuple[str, str]]) -> str:
        """
        conversa: [(papel, texto)] com papel "user" ou "model", terminando no usuário.
        Devolve só o texto da resposta (sem os "pensamentos" do modelo).
        """
        corpo = {
            "systemInstruction": {"parts": [{"text": instrucoes}]},
            "contents": [{"role": papel, "parts": [{"text": texto}]} for papel, texto in conversa],
            "generationConfig": {"maxOutputTokens": self.max_tokens, "temperature": 0.9},
        }
        if self._usar_thinking:
            corpo["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}  # mais rápido

        resposta = self._post(corpo)
        if resposta.status_code == 400 and self._usar_thinking:
            # modelo sem suporte a thinkingLevel: tenta de novo sem e lembra disso
            log.warning("modelo %s recusou thinkingConfig; repetindo sem", self.modelo)
            self._usar_thinking = False
            corpo["generationConfig"].pop("thinkingConfig", None)
            resposta = self._post(corpo)

        if resposta.status_code == 429:
            raise ErroIA("cota do Gemini esgotada (429)", cota_esgotada=True)
        if resposta.status_code >= 400:
            raise ErroIA(f"Gemini respondeu {resposta.status_code}: {resposta.text[:300]}")

        try:
            dados = resposta.json()
            partes = dados["candidates"][0]["content"]["parts"]
        except (ValueError, KeyError, IndexError, TypeError) as erro:
            motivo = ""
            try:
                motivo = resposta.json().get("promptFeedback", {}).get("blockReason", "")
            except Exception:
                pass
            raise ErroIA(f"resposta sem texto do Gemini {motivo}".strip()) from erro

        texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
        if not texto.strip():
            raise ErroIA("Gemini devolveu texto vazio")
        return texto.strip()

    def _post(self, corpo: dict) -> requests.Response:
        try:
            return requests.post(
                URL.format(modelo=self.modelo),
                json=corpo,
                headers={"x-goog-api-key": self.chave, "Content-Type": "application/json"},
                timeout=TIMEOUT,
            )
        except requests.RequestException as erro:
            raise ErroIA(f"Gemini inacessível: {erro}") from erro
