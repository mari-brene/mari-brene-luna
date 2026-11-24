// Executa no navegador as ações devolvidas pela API.

import type { Acao, Link, TimerAtivo } from "./tipos";

export interface Executor {
  adicionarTimer: (timer: TimerAtivo) => void;
  cancelarTimers: () => void;
  encerrar: () => void;
}

const rotuloDaUrl = (url: string): string => {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (host.includes("spotify")) return "Abrir no Spotify";
    if (host.includes("youtube")) return "Abrir no YouTube";
    if (host.includes("google")) return "Abrir no Google";
    return `Abrir ${host}`;
  } catch {
    return "Abrir link";
  }
};

// crypto.randomUUID só existe em contexto seguro (https/localhost); este serve em qualquer lugar
let sequencia = 0;
const idTimer = () => `timer-${Date.now().toString(36)}-${(sequencia++).toString(36)}`;

const urlSegura = (url: unknown): url is string =>
  typeof url === "string" && /^https?:\/\//i.test(url);

/**
 * Executa as ações e devolve os links gerados. Os links também viram botões
 * na mensagem, porque o navegador pode bloquear a aba aberta automaticamente.
 */
export function executarAcoes(acoes: Acao[], executor: Executor): Link[] {
  const links: Link[] = [];
  for (const acao of acoes) {
    switch (acao.tipo) {
      case "abrir_url": {
        const url = acao.dados.url;
        if (!urlSegura(url)) break;
        links.push({ url, rotulo: rotuloDaUrl(url) });
        window.open(url, "_blank", "noopener,noreferrer");
        break;
      }
      case "timer": {
        const segundos = Number(acao.dados.segundos);
        if (!Number.isFinite(segundos) || segundos <= 0) break;
        executor.adicionarTimer({
          id: idTimer(),
          fim: Date.now() + segundos * 1000,
          mensagem: String(acao.dados.mensagem ?? "⏰ Tempo esgotado!"),
        });
        pedirPermissaoNotificacao();
        break;
      }
      case "cancelar_timers":
        executor.cancelarTimers();
        break;
      case "encerrar":
        executor.encerrar();
        break;
      default:
        // ações de desktop (abrir_programa, desligar...) não existem na web
        console.warn("Ação ignorada no navegador:", acao.tipo);
    }
  }
  return links;
}

export function pedirPermissaoNotificacao(): void {
  if ("Notification" in window && Notification.permission === "default") {
    void Notification.requestPermission();
  }
}

export function notificar(texto: string): void {
  if ("Notification" in window && Notification.permission === "granted" && document.hidden) {
    new Notification("Luna 🌙", { body: texto, icon: "/favicon.svg" });
  }
}
