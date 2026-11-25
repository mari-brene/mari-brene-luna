-- Tabela de lembretes da Luna.
-- Rode uma vez no Supabase: SQL Editor -> cole este arquivo -> Run.

create table if not exists public.lembretes (
  id         bigint generated always as identity primary key,
  usuario    text        not null check (char_length(usuario) between 1 and 64),
  texto      text        not null check (char_length(texto) between 1 and 500),
  criado_em  timestamptz not null default now()
);

-- a Luna sempre busca "os lembretes do usuário X, em ordem"
create index if not exists lembretes_usuario_id_idx on public.lembretes (usuario, id);

-- Permissão explícita para a API REST (a chave secret usa o papel service_role).
-- Necessária em projetos que não expõem tabelas novas automaticamente.
grant usage on schema public to service_role;
grant select, insert, delete on public.lembretes to service_role;
grant usage, select on sequence public.lembretes_id_seq to service_role;

-- RLS ligado e SEM policies: anon/publishable não leem nem gravam nada.
-- Só a API da Luna, com a chave secret (que ignora RLS), acessa a tabela.
alter table public.lembretes enable row level security;
