"""Limites de uso da IA, para um site público não esgotar a cota da chave."""

import threading
import time
from collections import defaultdict, deque


class LimitadorTaxa:
    """
    Janela deslizante em memória:
      - por sessão: no máximo `por_sessao` chamadas por `janela_sessao` segundos;
      - global: no máximo `global_por_minuto` chamadas por minuto (cota do plano gratuito).
    """

    def __init__(self, por_sessao: int = 20, janela_sessao: int = 3600, global_por_minuto: int = 10,
                 relogio=time.monotonic):
        self.por_sessao = por_sessao
        self.janela_sessao = janela_sessao
        self.global_por_minuto = global_por_minuto
        self._relogio = relogio
        self._sessoes: dict[str, deque[float]] = defaultdict(deque)
        self._global: deque[float] = deque()
        self._trava = threading.Lock()

    @staticmethod
    def _podar(fila: deque[float], limite: float) -> None:
        while fila and fila[0] <= limite:
            fila.popleft()

    def permitir(self, sessao_id: str) -> bool:
        agora = self._relogio()
        with self._trava:
            fila = self._sessoes[sessao_id]
            self._podar(fila, agora - self.janela_sessao)
            self._podar(self._global, agora - 60)
            if len(fila) >= self.por_sessao or len(self._global) >= self.global_por_minuto:
                return False
            fila.append(agora)
            self._global.append(agora)
            # não deixa o dicionário crescer para sempre
            if len(self._sessoes) > 10_000:
                for chave in [k for k, v in self._sessoes.items() if not v]:
                    del self._sessoes[chave]
            return True
