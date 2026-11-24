"""
Executor de ações do cliente desktop.

Recebe a Resposta do núcleo, fala cada Fala pelo `io` (voz ou texto) e
executa as ações no computador local.
"""

import logging
import os
import subprocess
import threading
import webbrowser

from ..core.resposta import Resposta

log = logging.getLogger("luna.executor")


class ExecutorLocal:
    def __init__(self, io, sistema: str):
        self.io = io
        self.sistema = sistema
        self.timers: list[threading.Timer] = []
        self.rodando = True

    def executar(self, resposta: Resposta) -> None:
        for f in resposta.falas:
            self.io.falar(f.texto, idioma=f.idioma)
        for acao in resposta.acoes:
            metodo = getattr(self, f"_acao_{acao.tipo}", None)
            if metodo is None:
                log.warning("ação desconhecida: %s", acao.tipo)
                continue
            try:
                metodo(**acao.dados)
            except Exception:
                log.exception("falha ao executar %s", acao.tipo)
                self.io.falar(f"Não consegui executar {acao.tipo}.")

    # ------------------------------------------------------------ ações
    def _acao_abrir_url(self, url: str) -> None:
        webbrowser.open(url)

    def _acao_timer(self, segundos: float, mensagem: str) -> None:
        t = threading.Timer(segundos, self.io.falar, args=(mensagem,))
        t.daemon = True
        t.start()
        self.timers.append(t)

    def _acao_cancelar_timers(self) -> None:
        for t in self.timers:
            t.cancel()
        self.timers.clear()

    def _acao_abrir_programa(self, comando: str, nome: str) -> None:
        subprocess.Popen(comando, shell=True)

    def _acao_desligar(self, minutos: int) -> None:
        cmd = f"shutdown /s /t {minutos * 60}" if self.sistema == "Windows" else f"shutdown -h +{minutos}"
        if os.system(cmd) != 0:
            self.io.falar("O sistema não deixou agendar o desligamento. Falta permissão de admin?")

    def _acao_cancelar_desligamento(self) -> None:
        os.system("shutdown /a" if self.sistema == "Windows" else "shutdown -c")

    def _acao_encerrar(self) -> None:
        self._acao_cancelar_timers()
        self.rodando = False
