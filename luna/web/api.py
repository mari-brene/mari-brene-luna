"""
API HTTP da Luna (FastAPI).

    uvicorn luna.web.api:app --reload
    # documentação interativa em http://localhost:8000/docs

Variáveis de ambiente:
    LUNA_CORS_ORIGINS   origens liberadas, separadas por vírgula
                        (padrão: http://localhost:3000)
    LUNA_DB             caminho do SQLite dos lembretes
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .servico import TAMANHO_MAXIMO_FRASE, FraseInvalida, ServicoLuna


# ------------------------------------------------------------------ modelos
class SessaoEntrada(BaseModel):
    sessao_id: str | None = Field(default=None, max_length=64, description="ID salvo no navegador, se houver")


class ComandoEntrada(BaseModel):
    frase: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_FRASE, examples=["clima em Joinville"])
    sessao_id: str | None = Field(default=None, max_length=64)


class FalaSaida(BaseModel):
    texto: str
    idioma: str


class AcaoSaida(BaseModel):
    tipo: str = Field(examples=["abrir_url"])
    dados: dict = Field(examples=[{"url": "https://open.spotify.com/search/Queen"}])


class RespostaSaida(BaseModel):
    sessao_id: str
    nova_sessao: bool
    falas: list[FalaSaida]
    acoes: list[AcaoSaida]
    habilidade: str | None
    aguardando_resposta: bool
    idioma_escuta: str | None


class HabilidadeSaida(BaseModel):
    nome: str
    descricao: str
    exemplo: str


# ---------------------------------------------------------------------- app
def _origens_cors() -> list[str]:
    valor = os.environ.get("LUNA_CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in valor.split(",") if o.strip()]


def criar_app(servico: ServicoLuna | None = None) -> FastAPI:
    servico = servico or ServicoLuna()
    app = FastAPI(
        title="Luna API",
        version="1.0.0",
        description="Assistente virtual Luna: envie uma frase e receba falas e ações para o cliente executar.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origens_cors(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/", include_in_schema=False)
    def raiz() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/api/saude", tags=["infra"])
    def saude() -> dict:
        return {"status": "ok"}

    @app.post("/api/sessoes", response_model=RespostaSaida, tags=["luna"])
    def iniciar_sessao(entrada: SessaoEntrada | None = None) -> dict:
        """Cria ou retoma uma sessão e devolve a saudação."""
        return servico.iniciar(entrada.sessao_id if entrada else None)

    @app.post("/api/comando", response_model=RespostaSaida, tags=["luna"])
    def comando(entrada: ComandoEntrada) -> dict:
        """Processa uma frase. Guarde o `sessao_id` devolvido e envie-o nas próximas chamadas."""
        try:
            return servico.comando(entrada.frase, entrada.sessao_id)
        except FraseInvalida as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro

    @app.get("/api/habilidades", response_model=list[HabilidadeSaida], tags=["luna"])
    def habilidades() -> list[dict]:
        """O que a Luna sabe fazer na web, com um exemplo de frase para cada."""
        return servico.habilidades()

    return app


app = criar_app()
