import { useEffect, useRef } from "react";
import type { Mensagem } from "../tipos";

interface Props {
  mensagens: Mensagem[];
  pensando: boolean;
  parcial: string;
}

const hora = (t: number) => new Date(t).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

export function Mensagens({ mensagens, pensando, parcial }: Props) {
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens, pensando, parcial]);

  return (
    <div className="mensagens" role="log" aria-live="polite" aria-label="Conversa com a Luna">
      {mensagens.map((m) => (
        <div key={m.id} className={`linha linha-${m.autor}`}>
          {m.autor === "luna" && <div className="avatar" aria-hidden="true">🌙</div>}
          <div className={`balao balao-${m.autor}`}>
            {m.falas.map((f, i) => (
              <p key={i} lang={f.idioma === "pt" ? "pt-BR" : f.idioma}>
                {f.texto}
              </p>
            ))}
            {m.links.length > 0 && (
              <div className="links">
                {m.links.map((l) => (
                  <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" className="link-acao">
                    {l.rotulo} ↗
                  </a>
                ))}
              </div>
            )}
            <time className="hora" dateTime={new Date(m.hora).toISOString()}>
              {hora(m.hora)}
            </time>
          </div>
        </div>
      ))}

      {parcial && (
        <div className="linha linha-voce">
          <div className="balao balao-voce balao-parcial">
            <p>{parcial}…</p>
          </div>
        </div>
      )}

      {pensando && (
        <div className="linha linha-luna">
          <div className="avatar" aria-hidden="true">🌙</div>
          <div className="balao balao-luna digitando" aria-label="Luna está pensando">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}
      <div ref={fim} />
    </div>
  );
}
