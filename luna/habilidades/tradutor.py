"""Tradutor entre português e outros idiomas (lib translate)."""

from ..core.personalidade import fala
from ..core.registro import habilidade

IDIOMAS = {
    "ingles": ("en", "inglês"), "espanhol": ("es", "espanhol"), "frances": ("fr", "francês"),
    "italiano": ("it", "italiano"), "alemao": ("de", "alemão"), "portugues": ("pt", "português"),
}
_GRUPO = "|".join(IDIOMAS)


@habilidade(
    rf"\btraduz(?:ir|a)?(?: (?P<frase>.+?))? (?:para|pro|pra) (?:o )?(?P<idioma>{_GRUPO})$",
    rf"\bcomo (?:se )?(?:diz|fala) (?P<frase>.+?) em (?P<idioma>{_GRUPO})$",
    descricao="Traduz frases", exemplo="Como se diz bom dia em francês?", livres=("frase",),
)
def traduzir(ctx, idioma, frase=None):
    destino, nome = IDIOMAS[idioma]
    if frase:
        _traduzir(ctx, frase, destino)
    elif destino == "pt":
        ctx.perguntar(fala("traduzir_ingles"), continuar=_continuar, idioma_escuta="en-US", destino=destino)
    else:
        ctx.perguntar(fala("traduzir_pergunta", idioma=nome), continuar=_continuar, destino=destino)


def _continuar(ctx, resposta: str, destino: str):
    _traduzir(ctx, resposta, destino)


def _traduzir(ctx, frase: str, destino: str) -> None:
    from translate import Translator  # import tardio

    origem = "en" if destino == "pt" else "pt"
    try:
        resultado = Translator(from_lang=origem, to_lang=destino).translate(frase)
    except Exception:
        ctx.dizer("tradutor_erro")
        return
    ctx.falar(resultado, idioma=destino)
