// Formatos da API da Luna (espelham luna/web/api.py)

export interface Fala {
  texto: string;
  idioma: string;
}

export interface Acao {
  tipo: string;
  dados: Record<string, unknown>;
}

export interface RespostaLuna {
  sessao_id: string;
  nova_sessao: boolean;
  falas: Fala[];
  acoes: Acao[];
  habilidade: string | null;
  aguardando_resposta: boolean;
  idioma_escuta: string | null;
  via_ia?: boolean;
}

export interface Habilidade {
  nome: string;
  descricao: string;
  exemplo: string;
}

// Estado da interface

export interface Link {
  url: string;
  rotulo: string;
}

export interface Mensagem {
  id: string;
  autor: "voce" | "luna";
  falas: Fala[];
  links: Link[];
  hora: number;
  ia?: boolean; // resposta passou pela IA (conversa ou comando interpretado)
}

export interface TimerAtivo {
  id: string;
  fim: number; // timestamp em ms
  mensagem: string;
}
