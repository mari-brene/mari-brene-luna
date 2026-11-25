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
from .registro import encontrar
from .resposta import Resposta
from .sessao import Sessao
from .texto import normalizar

log = logging.getLogger("luna")

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

        ctx.resposta.habilidade = hab.nome
        sessao.registrar(frase, hab.nome)
        try:
            hab.funcao(ctx, **args)
        except Exception:  # uma habilidade com erro não derruba a assistente
            log.exception("erro na habilidade %s", hab.nome)
            ctx.resposta.falas.clear()
            ctx.resposta.acoes.clear()
            ctx.dizer("erro")
        return ctx.resposta

    def _sem_comando(self, ctx: Contexto, frase: str) -> None:
        """Nenhuma habilidade reconheceu a frase: a IA responde, se estiver ligada."""
        if self.ia is None:
            ctx.dizer("nao_entendi")
            return
        texto, chave_fala = self.ia.responder(frase, ctx.sessao)
        if texto:
            ctx.resposta.habilidade = "ia.conversa"
            ctx.falar(texto)
        else:
            ctx.dizer(chave_fala or "nao_entendi")

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
        return ctx.resposta
