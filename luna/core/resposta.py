"""
Resposta estruturada de um comando.

O núcleo nunca fala nem executa nada sozinho: ele devolve uma Resposta e
quem a recebe (terminal, navegador, app...) decide como falar e como
executar cada ação. Assim o mesmo núcleo serve qualquer cliente.
"""

from dataclasses import asdict, dataclass, field


@dataclass
class Fala:
    texto: str
    idioma: str = "pt"


@dataclass
class Acao:
    """
    Tipos usados hoje:
      abrir_url              {url}
      timer                  {segundos, mensagem}
      cancelar_timers        {}
      abrir_programa         {comando, nome}        (só desktop)
      desligar               {minutos}              (só desktop)
      cancelar_desligamento  {}                     (só desktop)
      encerrar               {}
    """
    tipo: str
    dados: dict = field(default_factory=dict)


@dataclass
class Resposta:
    falas: list[Fala] = field(default_factory=list)
    acoes: list[Acao] = field(default_factory=list)
    habilidade: str | None = None       # nome da habilidade que respondeu (útil em testes/logs)
    aguardando_resposta: bool = False   # a Luna fez uma pergunta e espera a próxima frase
    idioma_escuta: str | None = None    # ex.: "en-US" quando a próxima frase será em inglês
    via_ia: bool = False                # o comando foi entendido pela IA (frase fora do padrão)

    @property
    def texto(self) -> str:
        return " ".join(f.texto for f in self.falas)

    def tem_acao(self, tipo: str) -> bool:
        return any(a.tipo == tipo for a in self.acoes)

    def para_dict(self) -> dict:
        return asdict(self)
