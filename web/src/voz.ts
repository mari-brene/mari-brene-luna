// Voz no navegador: reconhecimento (Web Speech API) e síntese (speechSynthesis).

import type { Fala } from "./tipos";

// ---------------------------------------------------------------- reconhecimento
// A Web Speech API não está nos tipos padrão do TypeScript; declaramos só o que usamos.
interface ResultadoReconhecimento {
  isFinal: boolean;
  0: { transcript: string };
}
interface EventoReconhecimento {
  resultIndex: number;
  results: ArrayLike<ResultadoReconhecimento>;
}
interface EventoErroReconhecimento {
  error: string;
}
interface Reconhecedor {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: EventoReconhecimento) => void) | null;
  onerror: ((e: EventoErroReconhecimento) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type ConstrutorReconhecedor = new () => Reconhecedor;

function construtor(): ConstrutorReconhecedor | null {
  const w = window as unknown as {
    SpeechRecognition?: ConstrutorReconhecedor;
    webkitSpeechRecognition?: ConstrutorReconhecedor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export const reconhecimentoDisponivel = (): boolean => construtor() !== null;

export interface OpcoesEscuta {
  idioma: string;
  aoParcial: (texto: string) => void;
  aoFinal: (texto: string) => void;
  aoTerminar: () => void;
  aoErro: (mensagem: string) => void;
}

const ERROS: Record<string, string> = {
  "not-allowed": "Sem permissão para usar o microfone. Libere nas configurações do navegador.",
  "service-not-allowed": "O navegador bloqueou o reconhecimento de voz.",
  "audio-capture": "Não encontrei nenhum microfone.",
  network: "O reconhecimento de voz precisa de internet.",
};

/** Escuta uma frase e devolve uma função para parar. */
export function escutar(opcoes: OpcoesEscuta): () => void {
  const Construtor = construtor();
  if (!Construtor) {
    opcoes.aoErro("Seu navegador não tem reconhecimento de voz. Use o Chrome ou o Edge, ou digite.");
    opcoes.aoTerminar();
    return () => {};
  }
  const rec = new Construtor();
  rec.lang = opcoes.idioma;
  rec.interimResults = true;
  rec.continuous = false;

  rec.onresult = (e) => {
    let parcial = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const resultado = e.results[i];
      if (resultado.isFinal) {
        opcoes.aoFinal(resultado[0].transcript.trim());
        return;
      }
      parcial += resultado[0].transcript;
    }
    opcoes.aoParcial(parcial);
  };
  rec.onerror = (e) => {
    // "no-speech" e "aborted" são normais (silêncio / parou de propósito)
    if (e.error !== "no-speech" && e.error !== "aborted") {
      opcoes.aoErro(ERROS[e.error] ?? `Erro no microfone: ${e.error}`);
    }
  };
  rec.onend = () => opcoes.aoTerminar();
  rec.start();
  return () => rec.stop();
}

// --------------------------------------------------------------------- síntese
const LOCALIDADE: Record<string, string> = {
  pt: "pt-BR",
  en: "en-US",
  es: "es-ES",
  fr: "fr-FR",
  it: "it-IT",
  de: "de-DE",
};

export const localidade = (idioma: string): string => LOCALIDADE[idioma] ?? idioma;

const EMOJI = /[\p{Extended_Pictographic}\u{FE0F}\u{200D}]/gu;
export const semEmoji = (texto: string): string => texto.replace(EMOJI, "").replace(/\s{2,}/g, " ").trim();

export const sinteseDisponivel = (): boolean => "speechSynthesis" in window;

function escolherVoz(loc: string): SpeechSynthesisVoice | undefined {
  const vozes = window.speechSynthesis.getVoices();
  const doIdioma = vozes.filter((v) => v.lang.replace("_", "-").toLowerCase().startsWith(loc.toLowerCase()));
  // preferimos vozes femininas/naturais conhecidas quando existirem
  const preferidas = ["Google português do Brasil", "Francisca", "Luciana", "Microsoft Francisca"];
  return doIdioma.find((v) => preferidas.some((p) => v.name.includes(p))) ?? doIdioma[0];
}

/** Fala as falas em sequência. Resolve quando termina (ou na hora, se estiver indisponível). */
export function falar(falas: Fala[]): Promise<void> {
  if (!sinteseDisponivel() || falas.length === 0) return Promise.resolve();
  const sintese = window.speechSynthesis;
  sintese.cancel();
  return new Promise((resolver) => {
    let restantes = falas.length;
    const terminar = () => {
      restantes -= 1;
      if (restantes <= 0) resolver();
    };
    for (const fala of falas) {
      const texto = semEmoji(fala.texto);
      if (!texto) {
        terminar();
        continue;
      }
      const u = new SpeechSynthesisUtterance(texto);
      u.lang = localidade(fala.idioma);
      const voz = escolherVoz(u.lang);
      if (voz) u.voice = voz;
      u.rate = 1.05;
      u.onend = terminar;
      u.onerror = terminar;
      sintese.speak(u);
    }
  });
}

export function calar(): void {
  if (sinteseDisponivel()) window.speechSynthesis.cancel();
}
