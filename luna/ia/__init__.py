"""
IA de conversa: entra quando nenhuma habilidade reconhece a frase.

Ela pode (1) responder conversando, ou (2) chamar a ferramenta
`executar_comando` com a frase reescrita no formato de um comando da Luna
("lembra de comprar pão depois do almoço" -> "lembrar de comprar pão depois
do almoço"; "e amanhã?" depois de clima em Curitiba -> "clima amanhã em
Curitiba"). Quem executa é sempre o roteador normal: a IA não tem acesso
direto a nada.

Provedores (cada um ativado pela sua chave; sem nenhuma, a Luna continua
dizendo "não entendi"). Os modelos são tentados em ordem: se um estiver
sobrecarregado, sem cota ou não existir, passa para o próximo, e o que
falhou fica "de castigo" por alguns minutos (não atrasa as próximas mensagens).

    provedor    chave                 modelo (variável / padrão)               plano
    gemini      GEMINI_API_KEY        GEMINI_MODELO / gemini-3.8-flash         gratuito
    groq        GROQ_API_KEY          GROQ_MODELO / openai/gpt-oss-120b        gratuito
    cerebras    CEREBRAS_API_KEY      CEREBRAS_MODELO / gpt-oss-120b           gratuito
    mistral     MISTRAL_API_KEY       MISTRAL_MODELO / mistral-small-latest    gratuito
    openrouter  OPENROUTER_API_KEY    OPENROUTER_MODELO / openrouter/free      gratuito (:free)
    grok        XAI_API_KEY           XAI_MODELO / grok-4-1-fast-reasoning     pago

    *_MODELO aceita lista separada por vírgula.
Opcionais:
    LUNA_IA_ORDEM          ordem (padrão: gemini,groq,cerebras,mistral,openrouter,grok)
    LUNA_IA_POR_SESSAO     chamadas por sessão por hora (padrão: 20)
    LUNA_IA_POR_MINUTO     chamadas por minuto no total (padrão: 10)
"""

import logging
import os
import re
import threading
import time
from dataclasses import dataclass

from ..core.relogio import agora as relogio_agora
from .gemini import ClienteGemini, ErroIA, RespostaModelo
from .limites import LimitadorTaxa
from .openai_compat import ClienteOpenAICompat

log = logging.getLogger("luna.ia")

MODELO_PADRAO = "gemini-3.8-flash"
ORDEM_PADRAO = "gemini,groq,cerebras,mistral,openrouter,grok"  # gratuitos primeiro, pago por último

# provedores no formato OpenAI: nome -> (variável da chave, variável do modelo, URL base, modelo padrão)
COMPATIVEIS = {
    "groq": ("GROQ_API_KEY", "GROQ_MODELO", "https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "cerebras": ("CEREBRAS_API_KEY", "CEREBRAS_MODELO", "https://api.cerebras.ai/v1", "gpt-oss-120b"),
    "mistral": ("MISTRAL_API_KEY", "MISTRAL_MODELO", "https://api.mistral.ai/v1", "mistral-small-latest"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODELO", "https://openrouter.ai/api/v1", "openrouter/free"),
    "grok": ("XAI_API_KEY", "XAI_MODELO", "https://api.x.ai/v1", "grok-4-1-fast-reasoning"),
}

# quanto tempo um modelo fica fora da fila depois de falhar (segundos)
PAUSA_SEM_COTA = 5 * 60          # 429: cota por minuto/dia; volta a tentar em 5 min
PAUSA_INDISPONIVEL = 3 * 60      # 5xx / timeout: sobrecarga (no plano gratuito costuma durar)
PAUSA_INEXISTENTE = 6 * 60 * 60  # 404: modelo não existe para essa chave
PAUSA_OUTROS = 10 * 60           # chave recusada, requisição recusada (400) etc.
ORCAMENTO_S = 25                 # tempo máximo tentando provedores numa mesma mensagem
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

    def __init__(self, cliente, limitador: LimitadorTaxa, relogio=time.monotonic):
        self.clientes = cliente if isinstance(cliente, list) else [cliente]
        self.limitador = limitador
        self._relogio = relogio
        self._pausados: dict[int, float] = {}  # índice do cliente -> até quando fica fora
        self._trava = threading.Lock()

    def _disponiveis(self) -> list:
        agora = self._relogio()
        with self._trava:
            return [c for i, c in enumerate(self.clientes) if self._pausados.get(i, 0) <= agora]

    def _pausar(self, cliente, erro: ErroIA) -> None:
        if erro.cota_esgotada:
            segundos = PAUSA_SEM_COTA
        elif erro.modelo_inexistente:
            segundos = PAUSA_INEXISTENTE
        elif erro.temporario:
            segundos = PAUSA_INDISPONIVEL
        else:
            segundos = PAUSA_OUTROS
        with self._trava:
            self._pausados[self.clientes.index(cliente)] = self._relogio() + segundos
        log.warning("%s fora da fila por %d s (%s)", _nome(cliente), segundos, erro)

    def estado(self) -> list[dict]:
        """Situação de cada modelo (para diagnóstico)."""
        agora = self._relogio()
        return [{"modelo": _nome(c), "pausado_por_s": max(0, round(self._pausados.get(i, 0) - agora))}
                for i, c in enumerate(self.clientes)]

    @property
    def cliente(self):
        return self.clientes[0]

    def _gerar(self, conversa: list[tuple[str, str]], exemplos: list[str]) -> RespostaModelo:
        """Tenta cada modelo da lista; passa para o próximo se o atual estiver indisponível."""
        lista = "\n".join(f"- {e}" for e in exemplos) or "- (nenhum)"
        instrucoes = INSTRUCOES.format(agora=_agora(), exemplos=lista)
        candidatos = self._disponiveis()
        if not candidatos:
            raise ErroIA("todos os modelos estão pausados (sem cota/indisponíveis)", cota_esgotada=True)
        ultimo_erro: ErroIA | None = None
        inicio = self._relogio()
        for cliente in candidatos:
            if self._relogio() - inicio > ORCAMENTO_S:
                log.warning("orçamento de %d s esgotado; desistindo desta mensagem", ORCAMENTO_S)
                raise ErroIA("tempo esgotado tentando os provedores", temporario=True)
            try:
                return cliente.gerar(instrucoes, conversa, ferramentas=[FERRAMENTA])
            except ErroIA as erro:
                # qualquer falha de um provedor passa para o próximo da fila;
                # erros que não são de cota/sobrecarga ficam como ERROR no log (configuração?)
                ultimo_erro = erro
                if not (erro.temporario or erro.modelo_inexistente or erro.cota_esgotada):
                    log.error("%s falhou: %s", _nome(cliente), erro)
                self._pausar(cliente, erro)
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


def _nome(cliente) -> str:
    return repr(cliente) if isinstance(cliente, ClienteOpenAICompat) else f"gemini:{cliente.modelo}"


def _lista(variavel: str, padrao: str) -> list[str]:
    valor = os.environ.get(variavel, "").strip() or padrao
    return [m.strip() for m in valor.split(",") if m.strip()]


def _clientes_gemini() -> list:
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    return [ClienteGemini(chave, m) for m in _lista("GEMINI_MODELO", MODELO_PADRAO)] if chave else []


def _clientes_compativeis(nome: str) -> list:
    var_chave, var_modelo, url, padrao = COMPATIVEIS[nome]
    chave = os.environ.get(var_chave, "").strip()
    if not chave:
        return []
    return [ClienteOpenAICompat(chave, m, url, nome) for m in _lista(var_modelo, padrao)]


def _clientes(nome: str) -> list:
    if nome == "gemini":
        return _clientes_gemini()
    if nome in COMPATIVEIS:
        return _clientes_compativeis(nome)
    log.warning("provedor desconhecido em LUNA_IA_ORDEM: %s", nome)
    return []


def criar_conversa() -> Conversa | None:
    ordem = _lista("LUNA_IA_ORDEM", ORDEM_PADRAO)
    clientes = [c for nome in ordem for c in _clientes(nome)]
    if not clientes:
        return None
    limitador = LimitadorTaxa(
        por_sessao=int(os.environ.get("LUNA_IA_POR_SESSAO", 20)),
        global_por_minuto=int(os.environ.get("LUNA_IA_POR_MINUTO", 10)),
    )
    log.info("IA ativada com o(s) modelo(s) %s", ", ".join(_nome(c) for c in clientes))
    return Conversa(clientes, limitador)


__all__ = ["Conversa", "ClienteGemini", "ClienteOpenAICompat", "ErroIA", "LimitadorTaxa", "ResultadoIA",
           "criar_conversa", "FERRAMENTA"]
