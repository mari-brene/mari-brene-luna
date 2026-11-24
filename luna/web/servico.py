"""
Casos de uso da versão web, sem depender de framework HTTP.

A API (api.py) só traduz HTTP <-> estes métodos. Assim a lógica é testável
sem servidor e trocar FastAPI por outro framework não mexe aqui.
"""

from ..core.assistente import Luna
from ..core.contexto import carregar_config
from ..core.registro import disponiveis
from ..core.resposta import Resposta
from .sessoes import RepositorioSessoes

TAMANHO_MAXIMO_FRASE = 500


class FraseInvalida(ValueError):
    pass


class ServicoLuna:
    def __init__(self, config: dict | None = None, sessoes: RepositorioSessoes | None = None):
        self.luna = Luna(config or carregar_config(), plataforma="web")
        self.sessoes = sessoes or RepositorioSessoes()

    def iniciar(self, sessao_id: str | None = None) -> dict:
        """Cria (ou retoma) a sessão e devolve a saudação da Luna."""
        sessao, nova = self.sessoes.obter(sessao_id)
        resposta = self.luna.saudacao(sessao, exigir_ativacao=False)
        return self._saida(resposta, sessao.id, nova)

    def comando(self, frase: str, sessao_id: str | None = None) -> dict:
        frase = (frase or "").strip()
        if not frase:
            raise FraseInvalida("A frase está vazia.")
        if len(frase) > TAMANHO_MAXIMO_FRASE:
            raise FraseInvalida(f"A frase passa de {TAMANHO_MAXIMO_FRASE} caracteres.")
        sessao, nova = self.sessoes.obter(sessao_id)
        resposta = self.luna.processar(frase, sessao)
        return self._saida(resposta, sessao.id, nova)

    def habilidades(self) -> list[dict]:
        return [
            {"nome": h.nome, "descricao": h.descricao, "exemplo": h.exemplo}
            for h in disponiveis("web") if h.exemplo
        ]

    @staticmethod
    def _saida(resposta: Resposta, sessao_id: str, nova: bool) -> dict:
        return {"sessao_id": sessao_id, "nova_sessao": nova, **resposta.para_dict()}
