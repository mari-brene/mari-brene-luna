import { useEffect, useRef } from "react";
import type { Habilidade } from "../tipos";

interface Props {
  aberta: boolean;
  habilidades: Habilidade[];
  aoEscolher: (frase: string) => void;
  aoFechar: () => void;
}

export function Ajuda({ aberta, habilidades, aoEscolher, aoFechar }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = dialogo.current;
    if (!d) return;
    if (aberta && !d.open) d.showModal();
    if (!aberta && d.open) d.close();
  }, [aberta]);

  return (
    <dialog
      ref={dialogo}
      className="ajuda"
      onClose={aoFechar}
      onClick={(e) => e.target === dialogo.current && aoFechar()}
      aria-labelledby="ajuda-titulo"
    >
      <header>
        <h2 id="ajuda-titulo">O que eu sei fazer</h2>
        <button type="button" onClick={aoFechar} aria-label="Fechar">
          ×
        </button>
      </header>
      {habilidades.length === 0 ? (
        <p className="ajuda-vazia">Carregando meus comandos…</p>
      ) : (
        <ul>
          {habilidades.map((h) => (
            <li key={h.nome}>
              <button
                type="button"
                onClick={() => {
                  aoEscolher(h.exemplo);
                  aoFechar();
                }}
              >
                <strong>{h.descricao}</strong>
                <span>“{h.exemplo}”</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="ajuda-rodape">Toque num exemplo para testar. Também tenho alguns easter eggs escondidos 👀</p>
    </dialog>
  );
}

const SUGESTOES = ["Que horas são?", "Vai chover amanhã?", "Conta uma piada", "Lembrar de beber água", "Timer de 1 minuto"];

export function Sugestoes({ aoEscolher }: { aoEscolher: (frase: string) => void }) {
  return (
    <div className="sugestoes" aria-label="Sugestões">
      {SUGESTOES.map((s) => (
        <button key={s} type="button" onClick={() => aoEscolher(s)}>
          {s}
        </button>
      ))}
    </div>
  );
}
