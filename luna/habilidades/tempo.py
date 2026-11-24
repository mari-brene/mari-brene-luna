"""Hora, data, timer e pomodoro."""

from datetime import datetime

from ..core.personalidade import fala
from ..core.registro import habilidade
from ..core.texto import para_numero

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

@habilidade(r"\b(que horas|horas sao|horario)\b", descricao="Diz a hora", exemplo="Que horas são?")
def hora(ctx):
    agora = datetime.now()
    ctx.dizer("hora", hora=f"{agora.hour}h{agora.minute:02d}")


@habilidade(r"\b(que dia|data de hoje|dia e hoje)\b", descricao="Diz a data", exemplo="Que dia é hoje?")
def data(ctx):
    hoje = datetime.now()
    ctx.dizer("data", data=f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}")


@habilidade(
    r"(?:timer|cronometro|alarme) de (?P<qtd>[\w,.]+) (?P<unidade>segundo|minuto|hora)s?",
    r"me avis[ae] (?:daqui a|em) (?P<qtd>[\w,.]+) (?P<unidade>segundo|minuto|hora)s?",
    descricao="Timer", exemplo="Timer de 10 minutos",
)
def timer(ctx, qtd, unidade):
    n = para_numero(qtd)
    if not n:
        ctx.dizer("timer_invalido")
        return
    fator = {"segundo": 1, "minuto": 60, "hora": 3600}[unidade]
    tempo = f"{qtd} {unidade}{'s' if n != 1 else ''}"
    ctx.agendar(n * fator, fala("timer_fim", tempo=tempo))
    ctx.dizer("timer_ok", tempo=tempo)


@habilidade(r"\b(iniciar|comecar) pomodoro\b", r"^pomodoro$",
            descricao="Ciclo pomodoro", exemplo="Iniciar pomodoro", prioridade=2)
def pomodoro(ctx):
    foco = ctx.config["pomodoro"]["foco_min"]
    pausa = ctx.config["pomodoro"]["pausa_min"]
    ctx.agendar(foco * 60, fala("pomodoro_pausa", pausa=pausa))
    ctx.agendar((foco + pausa) * 60, fala("pomodoro_volta"))
    ctx.dizer("pomodoro_ok", foco=foco, pausa=pausa)


@habilidade(r"\bcancelar (?:os )?(?:timers?|pomodoro|alarmes?)\b", descricao="Cancela timers", prioridade=5)
def cancelar_timers(ctx):
    # quem guarda os timers é o cliente; aqui só pedimos o cancelamento
    ctx.acao("cancelar_timers")
    ctx.dizer("timers_cancelados")
