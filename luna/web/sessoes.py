"""
Sessões da versão web, guardadas em memória.

O ID da sessão é gerado pelo servidor e o navegador o guarda (localStorage),
então ele também identifica o usuário: os lembretes ficam presos a ele.

Limitação conhecida: em memória, as sessões somem quando o processo reinicia
(e não são compartilhadas entre instâncias/serverless). O que se perde é só
uma pergunta pendente; lembretes ficam no banco. Para escalar, trocar por
Redis/Supabase mantendo a mesma interface.
"""

import re
import secrets
import threading
import time
from collections import OrderedDict

from ..core.sessao import Sessao

_ID_VALIDO = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def novo_id() -> str:
    return secrets.token_urlsafe(18)  # 24 caracteres, imprevisível


def id_valido(sessao_id: str | None) -> bool:
    return bool(sessao_id and _ID_VALIDO.match(sessao_id))


class RepositorioSessoes:
    def __init__(self, ttl_segundos: int = 30 * 60, maximo: int = 10_000, relogio=time.monotonic):
        self.ttl = ttl_segundos
        self.maximo = maximo
        self._relogio = relogio
        self._sessoes: OrderedDict[str, tuple[Sessao, float]] = OrderedDict()
        self._trava = threading.Lock()

    def __len__(self) -> int:
        return len(self._sessoes)

    def obter(self, sessao_id: str | None) -> tuple[Sessao, bool]:
        """
        Devolve (sessao, nova). Um ID válido mas desconhecido (ex.: servidor
        reiniciou) é reaproveitado, para o usuário não perder os lembretes.
        Um ID ausente ou inválido gera um novo.
        """
        agora = self._relogio()
        with self._trava:
            self._expirar(agora)
            if id_valido(sessao_id) and sessao_id in self._sessoes:
                sessao, _ = self._sessoes.pop(sessao_id)
                self._sessoes[sessao_id] = (sessao, agora)  # move para o fim (mais recente)
                return sessao, False
            sessao = Sessao(id=sessao_id if id_valido(sessao_id) else novo_id())
            self._sessoes[sessao.id] = (sessao, agora)
            while len(self._sessoes) > self.maximo:
                self._sessoes.popitem(last=False)  # descarta a menos usada
            return sessao, True

    def _expirar(self, agora: float) -> None:
        while self._sessoes:
            sessao_id, (_, visto) = next(iter(self._sessoes.items()))
            if agora - visto <= self.ttl:
                break
            del self._sessoes[sessao_id]
