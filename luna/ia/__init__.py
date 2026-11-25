"""
IA de conversa: entra quando nenhuma habilidade reconhece a frase.

Ela pode (1) responder conversando, ou (2) chamar a ferramenta
`executar_comando` com a frase reescrita no formato de um comando da Luna
("lembra de comprar pão depois do almoço" -> "lembrar de comprar pão depois
do almoço"; "e amanhã?" depois de clima em Curitiba -> "clima amanhã em
Curitiba"). Quem executa é sempre o roteador normal: a IA não tem acesso
direto a nada.

Ativada pela variável GEMINI_API_KEY (sem ela, a Luna continua dizendo
"não entendi"). Opcionais:
    GEMINI_MODELO          modelo, ou lista separada por vírgula tentada em ordem
                           quando um está sobrecarregado (padrão: gemini-3.8-flash)
    LUNA_IA_POR_SESSAO     chamadas por sessão por hora (padrão: 20)
    LUNA_IA_POR_MINUTO     chamadas por minuto no total (padrão: 10)
"""

import logging
import os
import re
from dataclasses import dataclass

from ..core.relogio import agora as relogio_agora
from .gemini import ClienteGemini, ErroIA, RespostaModelo
from .limites import LimitadorTaxa

log = logging.getLogger("luna.ia")

MODELO_PADRAO = "gemini-3.8-flash"
TURNOS_DE_MEMORIA = 6       # pares pergunta/resposta lembrados por sessão
TAMANHO_MAXIMO = 700        # caracteres falados, no máximo
TAMANHO_MAXIMO_COMANDO = 200

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

FERRAMENTA = {
    "name": "executar_comando",
    "description": (
        "Executa um dos comandos prontos da Luna (hora, timer, lembretes, clima, cotação, música, "
        "pesquisa, tradução etc.). Use quando o pedido do usuário corresponder a um deles."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "frase": {
                "type": "string",
                "description": "O pedido reescrito no formato de um dos exemplos de comando, em português, "
                               "completo e sem depender do contexto (ex.: 'clima amanhã em Curitiba').",
            }
        },
        "required": ["frase"],
    },
}

INSTRUCOES = """Você é a Luna, uma assistente virtual por voz, criada pela desenvolvedora Maria Clara Brene em Python.
Personalidade: descontraída, nerd (referências leves de programação e jogos) e com uma pitada de sarcasmo gentil. Nunca grosseira.

Você tem uma ferramenta, executar_comando, que roda os comandos prontos da Luna. Exemplos de frases que ela entende:
{exemplos}

Regras:
- Se o usuário pedir algo que um comando faz, CHAME executar_comando com a frase no formato dos exemplos, completa:
  traga do contexto o que faltar (ex.: depois de "clima em Curitiba", o usuário diz "e amanhã?" -> "clima amanhã em Curitiba").
- Para o resto (perguntas, curiosidades, conversa), responda você mesma, sem chamar a ferramenta.
- Nunca diga que fez algo (anotou, abriu, tocou) sem ter chamado a ferramenta.
- Responda SEMPRE em português do Brasil, a menos que peçam outro idioma.
- Suas respostas serão FALADAS: seja breve (no máximo 3 frases curtas), sem markdown, listas, links ou código, no máximo 1 emoji.
- Não invente fatos recentes, preços ou notícias (para isso existem os comandos); se não souber, diga com humor.
- Se perguntarem quem te criou ou como funciona: Python, FastAPI, React e Gemini, feita pela Maria Clara.
Agora: {agora}."""


@dataclass
class ResultadoIA:
    texto: str | None = None      # resposta de conversa, pronta para falar
    comando: str | None = None    # frase de comando que o núcleo deve executar
    fala: str | None = None       # chave de fala quando não deu certo ("ia_limite", "nao_entendi"...)


def _agora() -> str:
    d = relogio_agora()
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

    def __init__(self, cliente: ClienteGemini | list[ClienteGemini], limitador: LimitadorTaxa):
        self.clientes = cliente if isinstance(cliente, list) else [cliente]
        self.limitador = limitador

    @property
    def cliente(self) -> ClienteGemini:
        return self.clientes[0]

    def _gerar(self, conversa: list[tuple[str, str]], exemplos: list[str]) -> RespostaModelo:
        """Tenta cada modelo da lista; passa para o próximo se o atual estiver indisponível."""
        lista = "\n".join(f"- {e}" for e in exemplos) or "- (nenhum)"
        instrucoes = INSTRUCOES.format(agora=_agora(), exemplos=lista)
        ultimo_erro: ErroIA | None = None
        for cliente in self.clientes:
            try:
                return cliente.gerar(instrucoes, conversa, ferramentas=[FERRAMENTA])
            except ErroIA as erro:
                ultimo_erro = erro
                # cota (429) é por modelo: vale tentar o próximo também
                if not (erro.temporario or erro.modelo_inexistente or erro.cota_esgotada):
                    raise
                log.warning("modelo %s indisponível (%s); tentando o próximo", cliente.modelo, erro)
        assert ultimo_erro is not None
        raise ultimo_erro

    def responder(self, frase: str, sessao, exemplos: list[str] | None = None) -> ResultadoIA:
        if not self.limitador.permitir(sessao.id):
            return ResultadoIA(fala="ia_limite")
        conversa = [*sessao.memoria_ia, ("user", frase)]
        try:
            resposta = self._gerar(conversa, exemplos or [])
        except ErroIA as erro:
            log.error("falha na IA: %s", erro)
            if erro.cota_esgotada:
                return ResultadoIA(fala="ia_cansada")
            if erro.temporario:
                return ResultadoIA(fala="ia_sobrecarregada")
            return ResultadoIA(fala="nao_entendi")

        if resposta.chamada and resposta.chamada[0] == FERRAMENTA["name"]:
            comando = str(resposta.chamada[1].get("frase", "")).strip()[:TAMANHO_MAXIMO_COMANDO]
            if comando:
                log.info("IA traduziu %r -> comando %r", frase, comando)
                return ResultadoIA(comando=comando)
        if not resposta.texto:
            return ResultadoIA(fala="nao_entendi")
        texto = _limpar(resposta.texto)
        self.lembrar(sessao, frase, texto)
        return ResultadoIA(texto=texto)

    @staticmethod
    def lembrar(sessao, frase: str, resposta: str) -> None:
        """Guarda uma troca na memória curta da sessão (também usada para comandos)."""
        if not resposta:
            return
        sessao.memoria_ia.extend([("user", frase), ("model", resposta)])
        del sessao.memoria_ia[: -2 * TURNOS_DE_MEMORIA]


def criar_conversa() -> Conversa | None:
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None
    modelos = [m.strip() for m in os.environ.get("GEMINI_MODELO", "").split(",") if m.strip()] or [MODELO_PADRAO]
    clientes = [ClienteGemini(chave, m) for m in modelos]
    limitador = LimitadorTaxa(
        por_sessao=int(os.environ.get("LUNA_IA_POR_SESSAO", 20)),
        global_por_minuto=int(os.environ.get("LUNA_IA_POR_MINUTO", 10)),
    )
    log.info("IA ativada com o(s) modelo(s) %s", ", ".join(modelos))
    return Conversa(clientes, limitador)


__all__ = ["Conversa", "ClienteGemini", "ErroIA", "LimitadorTaxa", "ResultadoIA", "criar_conversa", "FERRAMENTA"]
