import { useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  desabilitado: boolean;
  ouvindo: boolean;
  temMicrofone: boolean;
  aoEnviar: (frase: string) => void;
  aoMicrofone: () => void;
}

export function Entrada({ desabilitado, ouvindo, temMicrofone, aoEnviar, aoMicrofone }: Props) {
  const [texto, setTexto] = useState("");

  const enviar = (e?: FormEvent) => {
    e?.preventDefault();
    const frase = texto.trim();
    if (!frase || desabilitado) return;
    aoEnviar(frase);
    setTexto("");
  };

  const teclas = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") setTexto("");
  };

  return (
    <form className="entrada" onSubmit={enviar}>
      {temMicrofone && (
        <button
          type="button"
          className={`microfone${ouvindo ? " ouvindo" : ""}`}
          onClick={aoMicrofone}
          disabled={desabilitado && !ouvindo}
          aria-pressed={ouvindo}
          aria-label={ouvindo ? "Parar de ouvir" : "Falar com a Luna"}
          title={ouvindo ? "Parar" : "Falar"}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-2.08A7 7 0 0 0 19 12h-2Z" />
          </svg>
        </button>
      )}
      <input
        type="text"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={teclas}
        placeholder={ouvindo ? "Ouvindo…" : "Digite ou fale com a Luna"}
        aria-label="Mensagem para a Luna"
        maxLength={500}
        disabled={desabilitado}
        autoComplete="off"
      />
      <button type="submit" className="enviar" disabled={desabilitado || !texto.trim()} aria-label="Enviar">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3.4 20.4 21 12 3.4 3.6 3.39 10.1 15 12 3.39 13.9z" />
        </svg>
      </button>
    </form>
  );
}
