"""
Cliente mínimo da API do Gemini (REST, generateContent), sem SDK.

A chave vai no header `x-goog-api-key`. O modelo é configurável porque os
nomes mudam com frequência (GEMINI_MODELO).
"""

import logging
import time
from dataclasses import dataclass

import requests

log = logging.getLogger("luna.ia")

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
TIMEOUT = 20
TEMPORARIOS = {500, 502, 503, 504}   # sobrecarga do lado do Google: vale tentar de novo
ESPERAS = (1.0, 2.5)                 # segundos entre as tentativas extras


class ErroIA(Exception):
    def __init__(self, mensagem: str, cota_esgotada: bool = False, temporario: bool = False,
                 modelo_inexistente: bool = False):
        super().__init__(mensagem)
        self.cota_esgotada = cota_esgotada
        self.temporario = temporario
        self.modelo_inexistente = modelo_inexistente


@dataclass
class RespostaModelo:
    texto: str = ""
    chamada: tuple[str, dict] | None = None  # (nome da função, argumentos)


class ClienteGemini:
    def __init__(self, chave: str, modelo: str, max_tokens: int = 400):
        self.chave = chave
        self.modelo = modelo
        self.max_tokens = max_tokens
        self._usar_thinking = True  # desliga sozinho se o modelo não aceitar

    def gerar(self, instrucoes: str, conversa: list[tuple[str, str]],
              ferramentas: list[dict] | None = None) -> RespostaModelo:
        """
        conversa: [(papel, texto)] com papel "user" ou "model", terminando no usuário.
        ferramentas: declarações de funções (function calling) que o modelo pode chamar.
        Devolve o texto (sem os "pensamentos" do modelo) e/ou a função chamada.
        """
        corpo = {
            "systemInstruction": {"parts": [{"text": instrucoes}]},
            "contents": [{"role": papel, "parts": [{"text": texto}]} for papel, texto in conversa],
            "generationConfig": {"maxOutputTokens": self.max_tokens, "temperature": 0.9},
        }
        if ferramentas:
            corpo["tools"] = [{"functionDeclarations": ferramentas}]
        if self._usar_thinking:
            corpo["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}  # mais rápido

        resposta = self._post(corpo)
        if resposta.status_code == 400 and self._usar_thinking:
            # modelo sem suporte a thinkingLevel: tenta de novo sem e lembra disso
            log.warning("modelo %s recusou thinkingConfig; repetindo sem", self.modelo)
            self._usar_thinking = False
            corpo["generationConfig"].pop("thinkingConfig", None)
            resposta = self._post(corpo)

        for espera in ESPERAS:
            if resposta.status_code not in TEMPORARIOS:
                break
            log.warning("Gemini respondeu %s (%s) com %s; tentando de novo em %.1fs",
                        resposta.status_code, self._motivo(resposta), self.modelo, espera)
            self._dormir(espera)
            resposta = self._post(corpo)

        if resposta.status_code == 429:
            raise ErroIA(f"cota do Gemini esgotada (429): {self._motivo(resposta)}", cota_esgotada=True)
        if resposta.status_code in TEMPORARIOS:
            raise ErroIA(f"Gemini indisponível ({resposta.status_code}): {self._motivo(resposta)}", temporario=True)
        if resposta.status_code == 404:
            raise ErroIA(f"modelo {self.modelo} não encontrado (404)", modelo_inexistente=True)
        if resposta.status_code >= 400:
            raise ErroIA(f"Gemini respondeu {resposta.status_code}: {self._motivo(resposta)}")

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

        chamada = None
        for parte in partes:
            funcao = parte.get("functionCall")
            if isinstance(funcao, dict) and funcao.get("name"):
                chamada = (funcao["name"], funcao.get("args") or {})
                break
        texto = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
        if not texto and not chamada:
            raise ErroIA("Gemini devolveu texto vazio")
        return RespostaModelo(texto=texto, chamada=chamada)

    @staticmethod
    def _motivo(resposta: requests.Response) -> str:
        """Extrai a mensagem de erro do Google (error.status + error.message), se houver."""
        try:
            erro = resposta.json().get("error", {})
            if isinstance(erro, dict) and (erro.get("message") or erro.get("status")):
                return f"{erro.get('status', '')} {erro.get('message', '')}".strip()[:300]
        except Exception:
            pass
        return resposta.text[:300]

    @staticmethod
    def _dormir(segundos: float) -> None:
        time.sleep(segundos)

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
