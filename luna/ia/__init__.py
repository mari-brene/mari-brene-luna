"""
IA de conversa: responde quando nenhuma habilidade reconhece a frase.

Ativada pela variável GEMINI_API_KEY (sem ela, a Luna continua dizendo
"não entendi"). Opcionais:
    GEMINI_MODELO          modelo (padrão: gemini-3.8-flash)
    LUNA_IA_POR_SESSAO     chamadas por sessão por hora (padrão: 20)
    LUNA_IA_POR_MINUTO     chamadas por minuto no total (padrão: 10)
"""

import logging
import os
import re
from datetime import datetime

from .gemini import ClienteGemini, ErroIA
from .limites import LimitadorTaxa

log = logging.getLogger("luna.ia")

MODELO_PADRAO = "gemini-3.8-flash"
TURNOS_DE_MEMORIA = 6       # pares pergunta/resposta lembrados por sessão
TAMANHO_MAXIMO = 700        # caracteres falados, no máximo

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

INSTRUCOES = """Você é a Luna, uma assistente virtual por voz, criada pela desenvolvedora Maria Clara Brene em Python.
Personalidade: descontraída, nerd (referências leves de programação e jogos) e com uma pitada de sarcasmo gentil. Nunca grosseira.
Regras:
- Responda SEMPRE em português do Brasil, a menos que peçam outro idioma.
- Suas respostas serão FALADAS em voz alta: seja breve (no máximo 3 frases curtas), sem markdown, sem listas, sem links, sem código, no máximo 1 emoji.
- Você está respondendo porque a frase não era um dos seus comandos prontos. Seus comandos prontos são: hora e data, timer e pomodoro, pesquisa no Google/YouTube, Wikipédia, cotação e conversão de moedas, clima, notícias, tocar música, tradução, lembretes, piadas. Se a pessoa parecer querer um deles, sugira a frase certa (ex.: "diga: timer de 5 minutos").
- Você NÃO executa ações aqui: nunca diga que criou lembrete, abriu site, tocou música etc.
- Não invente fatos recentes, preços ou notícias; se não souber, diga com humor que não sabe.
- Se perguntarem quem te criou ou como funciona: Python, FastAPI, React e Gemini, feita pela Maria Clara.
Agora: {agora}."""


def _agora() -> str:
    d = datetime.now()
    return f"{DIAS[d.weekday()]}, {d.strftime('%d/%m/%Y %H:%M')}"


def _limpar(texto: str) -> str:
    """Tira markdown que atrapalharia a fala e corta respostas longas."""
    texto = re.sub(r"[*_`#>]+", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) > TAMANHO_MAXIMO:
        corte = texto[:TAMANHO_MAXIMO]
        fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "))
        texto = corte[: fim + 1] if fim > 100 else corte.rstrip() + "…"
    return texto


class Conversa:
    """Fallback de IA usado pelo núcleo. Guarda um histórico curto por sessão."""

    def __init__(self, cliente: ClienteGemini, limitador: LimitadorTaxa):
        self.cliente = cliente
        self.limitador = limitador

    def responder(self, frase: str, sessao) -> tuple[str | None, str | None]:
        """
        Devolve (texto, None) em caso de sucesso, ou (None, chave_de_fala) com
        a fala a usar quando não deu: "ia_limite", "ia_cansada" ou "nao_entendi".
        """
        if not self.limitador.permitir(sessao.id):
            return None, "ia_limite"
        historico: list[tuple[str, str]] = sessao.memoria_ia
        conversa = [*historico, ("user", frase)]
        try:
            texto = _limpar(self.cliente.gerar(INSTRUCOES.format(agora=_agora()), conversa))
        except ErroIA as erro:
            log.error("falha na IA: %s", erro)
            return None, "ia_cansada" if erro.cota_esgotada else "nao_entendi"
        historico.extend([("user", frase), ("model", texto)])
        del historico[: -2 * TURNOS_DE_MEMORIA]
        return texto, None


def criar_conversa() -> Conversa | None:
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    cliente = ClienteGemini(chave, os.environ.get("GEMINI_MODELO", "").strip() or MODELO_PADRAO)
    limitador = LimitadorTaxa(
        por_sessao=int(os.environ.get("LUNA_IA_POR_SESSAO", 20)),
        global_por_minuto=int(os.environ.get("LUNA_IA_POR_MINUTO", 10)),
    )
    log.info("IA ativada com o modelo %s", cliente.modelo)
    return Conversa(cliente, limitador)


__all__ = ["Conversa", "ClienteGemini", "ErroIA", "LimitadorTaxa", "criar_conversa"]
