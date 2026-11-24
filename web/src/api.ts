import type { Habilidade, RespostaLuna } from "./tipos";

const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const TEMPO_LIMITE_MS = 15_000;

export class ErroApi extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ErroApi";
  }
}

async function requisitar<T>(caminho: string, init?: RequestInit): Promise<T> {
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), TEMPO_LIMITE_MS);
  try {
    const resposta = await fetch(`${BASE}${caminho}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      signal: controle.signal,
    });
    if (!resposta.ok) {
      let detalhe = `Erro ${resposta.status}`;
      try {
        const corpo = await resposta.json();
        if (typeof corpo?.detail === "string") detalhe = corpo.detail;
      } catch {
        /* corpo não é JSON */
      }
      throw new ErroApi(detalhe, resposta.status);
    }
    return (await resposta.json()) as T;
  } catch (erro) {
    if (erro instanceof ErroApi) throw erro;
    throw new ErroApi("Não consegui falar com o servidor da Luna.");
  } finally {
    clearTimeout(relogio);
  }
}

export function iniciarSessao(sessaoId: string | null): Promise<RespostaLuna> {
  return requisitar("/api/sessoes", {
    method: "POST",
    body: JSON.stringify({ sessao_id: sessaoId }),
  });
}

export function enviarComando(frase: string, sessaoId: string | null): Promise<RespostaLuna> {
  return requisitar("/api/comando", {
    method: "POST",
    body: JSON.stringify({ frase, sessao_id: sessaoId }),
  });
}

export function listarHabilidades(): Promise<Habilidade[]> {
  return requisitar("/api/habilidades");
}
