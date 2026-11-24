"""Tradutor entre português e outros idiomas (lib translate)."""

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
    from translate import Translator  # import tardio

    destino, nome = IDIOMAS[idioma]
    if destino == "pt":
        frase = frase or ctx.ouvir(_pergunta(ctx, "traduzir_ingles"), tempo_limite=8, idioma="en-US")
        origem = "en"
    else:
        frase = frase or ctx.ouvir(_pergunta(ctx, "traduzir_pergunta", idioma=nome), tempo_limite=8)
        origem = "pt"
    if not frase:
        ctx.dizer("frase_vazia")
        return
    try:
        resultado = Translator(from_lang=origem, to_lang=destino).translate(frase)
    except Exception:
        ctx.dizer("tradutor_erro")
        return
    ctx.falar(resultado, idioma=destino)


def _pergunta(ctx, chave, **valores) -> str:
    from ..core.personalidade import fala
    return fala(chave, **valores)
