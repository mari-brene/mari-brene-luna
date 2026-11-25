"""
Lembretes e anotações, separados por usuário (ctx.sessao.id).

Onde ficam guardados (SQLite ou Supabase) é decidido em luna/armazenamento;
aqui só existe a conversa.
"""

import logging
from functools import wraps

from ..armazenamento import ErroArmazenamento, repositorio_lembretes
from ..core.personalidade import fala
from ..core.registro import habilidade
from ..core.texto import para_numero

log = logging.getLogger("luna.lembretes")


def _protegido(funcao):
    """Banco fora do ar vira uma fala amigável, não um erro genérico."""
    @wraps(funcao)
    def envolvida(ctx, *args, **kwargs):
        try:
            return funcao(ctx, *args, **kwargs)
        except ErroArmazenamento as erro:
            log.error("falha nos lembretes (%s): %s", funcao.__name__, erro)
            ctx.resposta.falas.clear()
            ctx.dizer("lembretes_erro")
    return envolvida


@habilidade(
    r"^(?:me )?lembr(?:e|ar)(?:-me)? de (?P<texto>.+)$",
    r"^(?:anot[ae]r?|anota ai) (?:que )?(?P<texto>.+)$",
    r"\b(?:criar|novo) (?:um )?lembrete\b(?: (?:de|para|que) (?P<texto>.+))?",
    descricao="Cria lembrete", exemplo="Lembrar de pagar a internet", livres=("texto",),
)
def criar(ctx, texto=None):
    if not texto:
        ctx.perguntar(fala("lembrete_pergunta"), continuar=_salvar)
        return
    _salvar(ctx, texto)


@_protegido
def _salvar(ctx, resposta: str):
    repositorio_lembretes().adicionar(ctx.sessao.id, resposta)
    ctx.dizer("lembrete_ok", texto=resposta)


@habilidade(
    r"\b(?:apagar|excluir|remover|concluir) (?:o )?lembrete (?:numero )?(?P<num>\w+)\b",
    descricao="Apaga um lembrete", exemplo="Apagar lembrete 2", prioridade=3,
)
@_protegido
def apagar(ctx, num):
    n = para_numero(num)
    repo = repositorio_lembretes()
    lista = repo.listar(ctx.sessao.id)
    if not n or not 1 <= n <= len(lista):
        ctx.dizer("lembrete_inexistente")
        return
    alvo = lista[int(n) - 1]
    repo.remover(ctx.sessao.id, alvo.id)
    ctx.dizer("lembrete_removido", texto=alvo.texto)


@habilidade(
    r"\b(?:apagar|limpar|excluir) (?:todos )?(?:os )?lembretes\b",
    descricao="Apaga todos os lembretes", prioridade=2,
)
@_protegido
def limpar(ctx):
    repositorio_lembretes().limpar(ctx.sessao.id)
    ctx.dizer("lembretes_limpos")


@habilidade(
    r"\b(?:ver|visualizar|listar|ler|quais (?:sao )?(?:os )?(?:meus )?)\s?(?:meus )?(?:lembretes|anotacoes)\b",
    r"^(?:meus )?lembretes$",
    descricao="Lista lembretes", exemplo="Ver lembretes",
)
@_protegido
def listar(ctx):
    lista = repositorio_lembretes().listar(ctx.sessao.id)
    if not lista:
        ctx.dizer("lembrete_vazio")
        return
    ctx.dizer("lembrete_lista", n=len(lista), s="s" if len(lista) > 1 else "")
    for i, lembrete in enumerate(lista, 1):
        ctx.falar(f"{i}. {lembrete.texto} (anotado em {lembrete.criado_em})")
