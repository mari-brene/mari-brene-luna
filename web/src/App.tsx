import { useCallback, useEffect, useRef, useState } from "react";
import { ErroApi, enviarComando, iniciarSessao, listarHabilidades } from "./api";
import { executarAcoes, notificar } from "./acoes";
import { Ajuda, Sugestoes } from "./componentes/Ajuda";
import { Entrada } from "./componentes/Entrada";
import { Mensagens } from "./componentes/Mensagens";
import { Timers } from "./componentes/Timers";
import type { Fala, Habilidade, Link, Mensagem } from "./tipos";
import { usarTimers } from "./usarTimers";
import { calar, escutar, falar, reconhecimentoDisponivel } from "./voz";

type Status = "conectando" | "online" | "offline";
type Origem = "texto" | "voz";

const CHAVE_SESSAO = "luna:sessao";
const CHAVE_MUDO = "luna:mudo";
const DEMORA_PARA_AVISO_MS = 3500; // depois disso, provavelmente o servidor gratuito estava dormindo

// localStorage pode lançar (modo privado, cookies bloqueados): nunca deixamos isso quebrar a app
const ler = (chave: string): string | null => {
  try {
    return localStorage.getItem(chave);
  } catch {
    return null;
  }
};
const gravar = (chave: string, valor: string) => {
  try {
    localStorage.setItem(chave, valor);
  } catch {
    /* ignora */
  }
};

let contador = 0;
const novoId = () => `${Date.now()}-${contador++}`;

export function App() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [status, setStatus] = useState<Status>("conectando");
  const [pensando, setPensando] = useState(false);
  const [ouvindo, setOuvindo] = useState(false);
  const [parcial, setParcial] = useState("");
  const [mudo, setMudo] = useState(() => ler(CHAVE_MUDO) === "1");
  const [aviso, setAviso] = useState<string | null>(null);
  const [ajudaAberta, setAjudaAberta] = useState(false);
  const [habilidades, setHabilidades] = useState<Habilidade[]>([]);
  const [acordando, setAcordando] = useState(false);

  const sessao = useRef<string | null>(ler(CHAVE_SESSAO));
  const mudoRef = useRef(mudo);
  const pararEscuta = useRef<(() => void) | null>(null);
  const iniciado = useRef(false);
  const temMicrofone = reconhecimentoDisponivel();

  const guardarSessao = (id: string) => {
    sessao.current = id;
    gravar(CHAVE_SESSAO, id);
  };

  const adicionar = useCallback((autor: Mensagem["autor"], falas: Fala[], links: Link[] = [], ia = false) => {
    if (falas.length === 0 && links.length === 0) return;
    setMensagens((lista) => [...lista, { id: novoId(), autor, falas, links, hora: Date.now(), ia }]);
  }, []);

  const dizer = useCallback(async (falas: Fala[]) => {
    if (!mudoRef.current) await falar(falas);
  }, []);

  const timers = usarTimers((timer) => {
    const falas = [{ texto: timer.mensagem, idioma: "pt" }];
    adicionar("luna", falas);
    notificar(timer.mensagem);
    void dizer(falas);
  });

  /** Se a resposta demorar, avisa que a Luna está acordando (servidor gratuito em repouso). */
  const avisandoDemora = useCallback(async <T,>(promessa: Promise<T>): Promise<T> => {
    const relogio = window.setTimeout(() => setAcordando(true), DEMORA_PARA_AVISO_MS);
    try {
      return await promessa;
    } finally {
      window.clearTimeout(relogio);
      setAcordando(false);
    }
  }, []);

  // ------------------------------------------------------------ conexão
  const conectar = useCallback(async () => {
    setStatus("conectando");
    setAviso(null);
    try {
      const r = await avisandoDemora(iniciarSessao(sessao.current));
      guardarSessao(r.sessao_id);
      setStatus("online");
      // saúda só quando a conversa está vazia (reconectar não repete a saudação)
      setMensagens((lista) =>
        lista.length > 0 ? lista : [{ id: novoId(), autor: "luna", falas: r.falas, links: [], hora: Date.now() }],
      );
      listarHabilidades().then(setHabilidades).catch(() => setHabilidades([]));
    } catch {
      setStatus("offline");
    }
  }, [avisandoDemora]);

  useEffect(() => {
    if (iniciado.current) return; // StrictMode monta duas vezes em dev
    iniciado.current = true;
    void conectar();
  }, [conectar]);

  // ------------------------------------------------------------ voz
  function ouvir(idioma = "pt-BR") {
    calar();
    setAviso(null);
    setParcial("");
    setOuvindo(true);
    let parar: (() => void) | null = null;
    parar = escutar({
      idioma,
      aoParcial: setParcial,
      aoFinal: (texto) => {
        setParcial("");
        if (texto) void enviar(texto, "voz");
      },
      aoTerminar: () => {
        // ignora o fim de uma escuta antiga se outra já começou (ex.: Luna perguntou algo)
        if (parar !== null && pararEscuta.current !== parar) return;
        setOuvindo(false);
        setParcial("");
        pararEscuta.current = null;
      },
      aoErro: setAviso,
    });
    pararEscuta.current = parar;
  }

  function alternarMicrofone() {
    if (ouvindo) pararEscuta.current?.();
    else ouvir();
  }

  function alternarMudo() {
    const novo = !mudo;
    setMudo(novo);
    mudoRef.current = novo;
    gravar(CHAVE_MUDO, novo ? "1" : "0");
    if (novo) calar();
  }

  // ------------------------------------------------------------ comando
  async function enviar(frase: string, origem: Origem) {
    frase = frase.trim();
    if (!frase || pensando) return;
    adicionar("voce", [{ texto: frase, idioma: "pt" }]);
    setPensando(true);
    setAviso(null);
    try {
      const r = await avisandoDemora(enviarComando(frase, sessao.current));
      guardarSessao(r.sessao_id);
      setStatus("online");
      const links = executarAcoes(r.acoes, {
        adicionarTimer: timers.adicionar,
        cancelarTimers: timers.cancelarTodos,
        encerrar: () => pararEscuta.current?.(),
      });
      setPensando(false);
      adicionar("luna", r.falas, links, Boolean(r.via_ia) || r.habilidade === "ia.conversa");
      await dizer(r.falas);
      // se a Luna perguntou algo e a conversa era por voz, já abre o microfone
      if (r.aguardando_resposta && origem === "voz" && temMicrofone) ouvir(r.idioma_escuta ?? "pt-BR");
    } catch (erro) {
      setPensando(false);
      if (erro instanceof ErroApi) {
        if (erro.status === undefined) setStatus("offline"); // sem resposta do servidor
        setAviso(erro.message);
      } else {
        console.error(erro);
        setAviso("Algo deu errado aqui no navegador. Tenta de novo?");
      }
    }
  }

  // ------------------------------------------------------------ tela
  const rotuloStatus = { conectando: "conectando…", online: "online", offline: "offline" }[status];

  return (
    <div className="app">
      <header className="topo">
        <div className="identidade">
          <div className="lua" aria-hidden="true" />
          <div>
            <h1>Luna</h1>
            <p className={`status status-${acordando ? "conectando" : status}`}>
              <span className="ponto" aria-hidden="true" />
              {acordando ? "acordando…" : ouvindo ? "ouvindo…" : pensando ? "pensando…" : rotuloStatus}
            </p>
          </div>
        </div>
        <div className="acoes-topo">
          <button
            type="button"
            className="icone"
            onClick={alternarMudo}
            aria-pressed={mudo}
            aria-label={mudo ? "Ativar voz da Luna" : "Silenciar a Luna"}
            title={mudo ? "Ativar voz" : "Silenciar"}
          >
            {mudo ? "🔇" : "🔊"}
          </button>
          <button
            type="button"
            className="icone"
            onClick={() => setAjudaAberta(true)}
            aria-label="O que a Luna sabe fazer"
            title="Ajuda"
          >
            ?
          </button>
        </div>
      </header>

      {acordando && (
        <div className="aviso aviso-info" role="status">
          <span>
            😴 A Luna estava dormindo. O servidor gratuito desliga quando ninguém usa, e acordar leva até 50 segundos.
          </span>
        </div>
      )}
      {status === "offline" && (
        <div className="aviso aviso-erro" role="alert">
          <span>A Luna está offline. O servidor pode estar acordando.</span>
          <button type="button" onClick={() => void conectar()}>
            Tentar de novo
          </button>
        </div>
      )}
      {aviso && status !== "offline" && (
        <div className="aviso" role="alert">
          <span>{aviso}</span>
          <button type="button" onClick={() => setAviso(null)} aria-label="Fechar aviso">
            ×
          </button>
        </div>
      )}

      <main className="conversa">
        <Mensagens mensagens={mensagens} pensando={pensando} parcial={parcial} />
      </main>

      <footer className="rodape">
        <Timers timers={timers.timers} aoCancelar={timers.cancelar} />
        {status === "online" && mensagens.length <= 1 && <Sugestoes aoEscolher={(f) => void enviar(f, "texto")} />}
        <Entrada
          desabilitado={status !== "online"}
          ouvindo={ouvindo}
          temMicrofone={temMicrofone}
          aoEnviar={(f) => void enviar(f, "texto")}
          aoMicrofone={alternarMicrofone}
        />
        {!temMicrofone && <p className="dica">Para falar com a Luna, use o Chrome ou o Edge.</p>}
      </footer>

      <Ajuda
        aberta={ajudaAberta}
        habilidades={habilidades}
        aoEscolher={(f) => void enviar(f, "texto")}
        aoFechar={() => setAjudaAberta(false)}
      />
    </div>
  );
}
