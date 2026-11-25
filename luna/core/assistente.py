"""
Núcleo da Luna: recebe uma frase e devolve uma Resposta.

    luna = Luna(carregar_config(), plataforma="web")
    sessao = Sessao()
    resposta = luna.processar("clima em Curitiba", sessao)
    resposta.falas  -> [Fala("Agora em Curitiba: ...")]
    resposta.acoes  -> []
"""

import logging
import platform as _platform
import re

from .contexto import Contexto
from .registro import disponiveis, encontrar
from .resposta import Resposta
from .sessao import Sessao
from .texto import normalizar

log = logging.getLogger("luna")

# a IA pode sugerir comandos, mas estes só valem se o usuário disser explicitamente
BLOQUEADOS_VIA_IA = {"sistema.desligar", "lembretes.limpar", "lembretes.apagar"}

# frases que desistem de uma pergunta pendente ("deixa pra lá")
_DESISTIR = re.compile(r"^(?:cancela(?:r)?|deixa (?:pra|para) la|esquece|nada|nao)$")


class Luna:
    def __init__(self, config: dict, plataforma: str = "desktop"):
        from .. import habilidades  # noqa: F401  (registra as habilidades)
        from ..ia import criar_conversa

        self.ia = criar_conversa()  # None se GEMINI_API_KEY não estiver definida

        self.config = config
        self.plataforma = plataforma
        self.sistema = _platform.system() if plataforma == "desktop" else ""

    def _contexto(self, sessao: Sessao, comando: str = "") -> Contexto:
        return Contexto(
            config=self.config, sessao=sessao, plataforma=self.plataforma,
            sistema=self.sistema, comando_atual=comando,
        )

    def saudacao(self, sessao: Sessao, exigir_ativacao: bool) -> Resposta:
        ctx = self._contexto(sessao)
        if exigir_ativacao:
            ctx.dizer("boas_vindas")
        else:
            ctx.dizer("boas_vindas_web" if self.plataforma == "web" else "boas_vindas_texto")
        return ctx.resposta

    def processar(self, frase: str, sessao: Sessao) -> Resposta:
        frase = frase.strip()
        if sessao.pendente:
            return self._continuar(frase, sessao)

        hab, args, comando = encontrar(frase, plataforma=self.plataforma)
        ctx = self._contexto(sessao, comando)
        if not hab:
            self._sem_comando(ctx, frase)
            sessao.registrar(frase, ctx.resposta.habilidade)
            return ctx.resposta

        sessao.registrar(frase, hab.nome)
        self._executar(ctx, hab, args)
        self._lembrar(sessao, frase, ctx.resposta)
        return ctx.resposta

    @staticmethod
    def _executar(ctx: Contexto, hab, args: dict) -> None:
        ctx.resposta.habilidade = hab.nome
        try:
            hab.funcao(ctx, **args)
        except Exception:  # uma habilidade com erro não derruba a assistente
            log.exception("erro na habilidade %s", hab.nome)
            ctx.resposta.falas.clear()
            ctx.resposta.acoes.clear()
            ctx.dizer("erro")

    def _lembrar(self, sessao: Sessao, frase: str, resposta: Resposta) -> None:
        """Comandos também entram na memória da IA, para ela entender "e amanhã?"."""
        if self.ia is not None and not resposta.aguardando_resposta:
            self.ia.lembrar(sessao, frase, resposta.texto)

    def _sem_comando(self, ctx: Contexto, frase: str) -> None:
        """Nenhuma habilidade reconheceu a frase: a IA conversa ou traduz para um comando."""
        if self.ia is None:
            ctx.dizer("nao_entendi")
            return
        exemplos = [h.exemplo for h in disponiveis(self.plataforma) if h.exemplo]
        resultado = self.ia.responder(frase, ctx.sessao, exemplos=exemplos)

        if resultado.comando:
            hab, args, comando = encontrar(resultado.comando, plataforma=self.plataforma)
            if hab is None:
                log.info("comando sugerido pela IA não reconhecido: %r", resultado.comando)
                ctx.dizer("nao_entendi")
                return
            if hab.nome in BLOQUEADOS_VIA_IA:
                ctx.dizer("confirmar_comando", frase=resultado.comando)
                return
            ctx.comando_atual = comando
            ctx.resposta.via_ia = True
            self._executar(ctx, hab, args)
            self._lembrar(ctx.sessao, frase, ctx.resposta)
        elif resultado.texto:
            ctx.resposta.habilidade = "ia.conversa"
            ctx.falar(resultado.texto)
        else:
            ctx.dizer(resultado.fala or "nao_entendi")

    def _continuar(self, frase: str, sessao: Sessao) -> Resposta:
        pendente, sessao.pendente = sessao.pendente, None
        comando = normalizar(frase)
        ctx = self._contexto(sessao, comando)
        ctx.resposta.habilidade = pendente.continuar.__name__
        if not comando or _DESISTIR.match(comando):
            ctx.dizer("desistiu")
            return ctx.resposta
        try:
            pendente.continuar(ctx, resposta=frase, **pendente.dados)
        except Exception:
            log.exception("erro na continuação %s", pendente.continuar.__name__)
            ctx.dizer("erro")
        self._lembrar(sessao, frase, ctx.resposta)
        return ctx.resposta
