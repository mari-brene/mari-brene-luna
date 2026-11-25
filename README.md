# 🌙 Luna — Assistente Virtual em Python

[![testes](https://github.com/mari-brene/mari-brene-luna/actions/workflows/testes.yml/badge.svg)](https://github.com/mari-brene/mari-brene-luna/actions/workflows/testes.yml)

**🌐 Experimente: [mari-brene-luna.vercel.app](https://mari-brene-luna.vercel.app)** · API: [luna-api-p1kw.onrender.com/docs](https://luna-api-p1kw.onrender.com/docs)

> A API roda no plano gratuito do Render e "dorme" depois de 15 minutos sem uso. A primeira mensagem pode levar até 50 segundos para acordar o servidor.

A Luna é uma assistente de voz em português. Você chama pelo nome — **"Luna, que horas são?"** — e ela executa e responde falando. Também roda em **modo texto**, para desenvolver e testar sem microfone.

## Personalidade

A Luna é **descontraída, nerd e com uma pitada de sarcasmo**. Ela nunca responde duas vezes seguidas com a mesma frase:

> **Você:** Luna, lembrar de revisar o currículo
> **Luna:** Salvei no banco: revisar o currículo. Commit feito ✅
>
> **Você:** Luna, cotação do bitcoin
> **Luna:** Bitcoin a 512 mil reais. Volátil igual meu humor 📈📉

Todas as falas ficam em `luna/core/personalidade.py`, separadas da lógica:

- `FALAS`: cada situação tem várias variações sorteadas.
- `PIADAS`: piadas de programação.
- `EASTER_EGGS`: respostas escondidas. Experimente "qual o sentido da vida", "sudo…", "tabs ou espaços", "funciona na minha máquina".

Os emojis aparecem no terminal, mas são removidos antes da síntese de voz.

## O que ela sabe fazer

| Área | Exemplos de comando |
|---|---|
| ⏰ Tempo | "Que horas são?" · "Que dia é hoje?" · "Timer de 10 minutos" · "Me avisa daqui a 5 minutos" · "Iniciar pomodoro" · "Cancelar timer" |
| 🔎 Web | "Pesquisar receita de bolo" · "Pesquisar lofi no YouTube" · "Quem foi Santos Dumont?" · "O que é fotossíntese?" (resumo da Wikipédia) |
| 💱 Finanças | "Cotação do dólar e do bitcoin" · "Quanto é 50 dólares em reais?" (USD, EUR, GBP, ARS, JPY, BTC, ETH) |
| ⛅ Clima | "Clima" (cidade padrão) · "Clima em Recife" · "Vai chover amanhã em Curitiba?" |
| 📰 Notícias | "Últimas notícias" · "Notícias sobre tecnologia" |
| 🎧 Música | "Tocar Legião Urbana" (Spotify) · "Tocar Queen no YouTube" |
| 🌍 Tradução | "Como se diz bom dia em francês?" · "Traduzir para o espanhol" · "Traduzir para o português" (ouve em inglês) |
| 📝 Lembretes | "Lembrar de pagar a internet" · "Anota que a reunião é às 15h" · "Ver lembretes" · "Apagar lembrete 2" · "Limpar lembretes" |
| 💻 Sistema | "Abrir Discord" · "Desligar o computador em 40 minutos" / "em meia hora" · "Cancelar desligamento" |
| 💬 Conversa | "Quem é você?" · "O que você sabe fazer?" · "Conta uma piada" · "Tchau" |

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-voz.txt   # modo voz (inclui o núcleo)
# ou só: pip install -r requirements.txt para o modo texto
```

`PyAudio` precisa do PortAudio: `sudo apt install portaudio19-dev` (Linux) ou `brew install portaudio` (macOS). No Windows o wheel já vem pronto. O `playsound` fica fixado em 1.2.2 porque a 1.3.0 tem bugs no Windows.

## Uso

```bash
python main.py                 # voz, exige dizer "Luna" antes do comando
python main.py --sem-ativacao  # voz, qualquer frase é comando
python main.py --texto         # teclado (não precisa de microfone nem das libs de áudio)
```

## API web

A mesma Luna, servida por HTTP para o front-end. O navegador cuida da voz e executa as ações; a API devolve falas e ações em JSON.

```bash
pip install -r requirements-web.txt
uvicorn luna.web.api:app --reload
# documentação interativa: http://localhost:8000/docs
```

| Rota | Corpo | Retorno |
|---|---|---|
| `GET /api/saude` | — | `{"status": "ok"}` |
| `POST /api/sessoes` | `{"sessao_id"?}` | saudação e o `sessao_id` |
| `POST /api/comando` | `{"frase", "sessao_id"?}` | resposta da Luna |
| `GET /api/habilidades` | — | `[{nome, descricao, exemplo}]` disponíveis na web |

```bash
curl -s localhost:8000/api/comando -H 'Content-Type: application/json' \
     -d '{"frase": "tocar Queen", "sessao_id": "SEU_ID"}'
```
```json
{
  "sessao_id": "ywWmLIwzThi4Unt5-5FGqh2D",
  "nova_sessao": false,
  "falas": [{"texto": "Bora de Queen! 🎶", "idioma": "pt"}],
  "acoes": [{"tipo": "abrir_url", "dados": {"url": "https://open.spotify.com/search/Queen"}}],
  "habilidade": "musica.tocar",
  "aguardando_resposta": false,
  "idioma_escuta": null
}
```

- **Sessão:** o servidor gera o `sessao_id` e o cliente o guarda (por exemplo no `localStorage`) para enviá-lo em todas as chamadas. Ele mantém as perguntas pendentes ("Qual é o lembrete?") e **separa os lembretes de cada usuário**.
- **Ações na web:** `abrir_url` abre uma nova aba, `timer` vira `setTimeout` com notificação, `cancelar_timers` limpa os timers e `encerrar` desliga o microfone. Abrir programas e desligar o PC só existem no desktop.
- **Segurança:**
  - o CORS só libera as origens definidas em `LUNA_CORS_ORIGINS` (separadas por vírgula; o padrão é `http://localhost:3000`);
  - frases têm limite de 500 caracteres;
  - IDs de sessão inválidos são descartados.
- **Sessões:** ficam em memória (30 min de inatividade, no máximo 10 mil). Se o servidor reiniciar, perde-se só uma pergunta pendente; os lembretes ficam no banco (veja "Lembretes no Supabase").

## Front-end web

Interface em **React + TypeScript (Vite)** na pasta `web/`: chat, botão de microfone e voz da Luna, tudo pelo navegador.

```bash
cd web
cp .env.example .env          # VITE_API_URL=http://localhost:8000
npm install
npm run dev                   # http://localhost:3000 (com a API rodando)
```

- **Voz:** usa a Web Speech API. O `SpeechRecognition` escuta e o `speechSynthesis` fala, sem custo e sem chave. O reconhecimento funciona no Chrome e no Edge; nos outros navegadores dá para digitar.
- **Ações no navegador:**
  - `abrir_url` abre uma nova aba e também vira um botão na mensagem, caso o navegador bloqueie o pop-up;
  - `timer` mostra uma contagem regressiva e avisa por voz e por notificação;
  - os timers podem ser cancelados por voz ou pelo ×.
- **Conversa por voz:** quando a Luna faz uma pergunta ("Qual é o lembrete?"), o microfone reabre sozinho. Na tradução para o português, ele escuta em inglês.
- **Estado no navegador:** a sessão (com os lembretes) e a opção de silenciar ficam no `localStorage`.
- **Ajuda:** o botão `?` lista as habilidades disponíveis na web; tocar num exemplo envia o comando.
- **Acessibilidade:** a conversa é um `role="log"` com `aria-live`, os botões têm rótulos, a navegação funciona pelo teclado e as animações respeitam `prefers-reduced-motion`.

### Teste ponta a ponta

`web/e2e/teste_front.py` abre o **build de produção no Chromium** (Playwright) e conversa com o `ServicoLuna` real, com a voz simulada. São 17 cenários: texto, voz, pergunta com o microfone reabrindo, timers, links, ajuda, mudo, recarregar a página, isolamento entre usuários, servidor offline e layout no celular.

```bash
cd web && npm run build && cd ..
pip install playwright && python -m playwright install chromium
python web/e2e/teste_front.py
```

## Deploy

| Parte | Onde | Como |
|---|---|---|
| API | Render | `render.yaml` na raiz (Blueprint). Defina `LUNA_CORS_ORIGINS` com a URL do front |
| Front | Vercel | Root Directory `web`, framework Vite, variável `VITE_API_URL` com a URL da API |

### Lembretes no Supabase

Sem configuração, os lembretes ficam em SQLite (`dados/luna.db`), o que é ótimo no desktop e em desenvolvimento. Em produção, o disco do Render é apagado a cada deploy, então os lembretes vão para o **Supabase**:

1. Crie um projeto no Supabase e rode `supabase/lembretes.sql` no SQL Editor. O arquivo cria a tabela com RLS ligado e sem policies, então só o backend acessa.
2. Em **Project Settings → API Keys**, copie a URL do projeto e uma chave **secret** (`sb_secret_...`).
3. No Render, defina `SUPABASE_URL` e `SUPABASE_SECRET_KEY`. Pronto: a API passa a usar o Supabase sozinha.

A conexão é feita pela API REST (PostgREST) com `requests`, sem SDK. A chave secret vai **só** no header `apikey`, porque as chaves novas não são JWT. A chave legada `service_role` também é aceita.

| Variável | Para quê |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SECRET_KEY` | ativam o Supabase (as duas juntas) |
| `LUNA_DB` | caminho do SQLite quando o Supabase não está configurado |
| `LUNA_FUSO` | fuso usado para mostrar as datas (padrão `America/Sao_Paulo`) |
| `LUNA_CORS_ORIGINS` | origens liberadas no CORS |
| `GEMINI_API_KEY` | ativa a IA de conversa |
| `GEMINI_MODELO`, `LUNA_IA_POR_SESSAO`, `LUNA_IA_POR_MINUTO` | modelo e limites da IA |

## IA de conversa (Gemini)

Quando nenhuma habilidade reconhece a frase, a Luna pode responder usando o **Gemini**, com a mesma personalidade e em respostas curtas, feitas para serem faladas. Sem chave, ela continua dizendo "não entendi".

```
"qual o maior planeta?"         → IA: "Júpiter, o grandalhão do sistema solar 🪐"
"e quantas luas ele tem?"       → IA lembra do contexto (6 últimas trocas por sessão)
"que horas são?"                → comando local, não gasta IA
```

- **Ativar:** crie uma chave grátis no Google AI Studio e defina `GEMINI_API_KEY` no servidor (no Render, nunca no front).
- **Implementação:** chamada REST ao `generateContent`, sem SDK (`luna/ia/`). Instruções de sistema com a persona, histórico curto por sessão, os "pensamentos" do modelo descartados, markdown removido e resposta cortada para caber na fala.
- **Proteção da cota:** limite por sessão (`LUNA_IA_POR_SESSAO`, padrão 20 por hora) e global (`LUNA_IA_POR_MINUTO`, padrão 10 por minuto). Quando estoura, a Luna avisa com humor e os comandos continuam funcionando.
- **Modelo:** `GEMINI_MODELO` (padrão `gemini-3.8-flash`). Se o modelo não aceitar `thinkingConfig`, o cliente repete a chamada sem ele.
- **Falhas:** rede, cota (429), bloqueio de segurança ou resposta vazia viram uma fala amigável e um log no servidor; nunca derrubam a API.

## Configuração — `config.json`

- `nome` / `palavra_ativacao`: identidade e a palavra que a desperta
- `cidade_padrao`: usada quando você pergunta só "clima"
- `pomodoro`: minutos de foco e pausa
- `programas` / `apelidos_programas`: o que ela consegue abrir, com o comando de cada sistema operacional (`Windows`, `Linux`, `Darwin`)

## Arquitetura

O **núcleo** recebe uma frase e devolve uma `Resposta` estruturada. Ele nunca fala nem executa nada sozinho. Quem decide **como** falar e **como** executar cada ação é o **cliente**: o terminal (`main.py`) ou o navegador, via API.

```
frase ──► Luna.processar(frase, sessao) ──► Resposta
                                              ├─ falas:  [Fala(texto, idioma)]
                                              ├─ acoes:  [Acao("abrir_url", {url}), Acao("timer", {segundos, mensagem}) ...]
                                              ├─ aguardando_resposta / idioma_escuta
                                              └─ habilidade: "clima.clima"
```

```
main.py                    cliente desktop: palavra de ativação + loop
config.json
luna/
  core/
    assistente.py          Luna.processar(): roteia, executa a habilidade, trata erros e perguntas pendentes
    resposta.py            Resposta, Fala, Acao (serializável em JSON)
    sessao.py              estado entre frases (pergunta pendente, histórico)
    contexto.py            o que a habilidade usa: falar, dizer, acao, abrir_url, agendar, perguntar
    registro.py            @habilidade: registro e roteamento por regex, com filtro de plataforma
    personalidade.py       todas as falas, piadas e easter eggs
    texto.py               normalização (sem acento/pontuação) com mapa para o texto original
  habilidades/             uma área por arquivo (sem efeitos colaterais: só montam a Resposta)
  ia/                      IA de conversa (Gemini via REST), persona e limites de uso
  armazenamento/            onde os lembretes ficam: SQLite (local) ou Supabase (produção)
  web/
    api.py                 FastAPI: rotas, validação (Pydantic), CORS
    servico.py             casos de uso da web, sem depender de framework
    sessoes.py             sessões em memória com TTL e limite
  clientes/
    executor.py            executa as ações no PC (navegador, timers, programas, shutdown)
    voz.py                 ModoVoz (SpeechRecognition + gTTS) e ModoTexto
tests/                     pytest: roteamento, habilidades (APIs mockadas), sessões, API
web/                       front-end React + TypeScript (Vite)
  src/App.tsx              conversa, envio de comandos, microfone
  src/api.ts               cliente da API (timeout, erros)
  src/voz.ts               Web Speech API: escutar e falar
  src/acoes.ts             executa as ações no navegador
  e2e/teste_front.py       teste ponta a ponta no Chromium
dados/luna.db              lembretes locais (SQLite; LUNA_DB muda o caminho)
supabase/lembretes.sql     tabela de lembretes para produção
```

### Plataformas

Algumas habilidades só existem no desktop, como abrir programas e desligar o PC. Elas são marcadas com `plataformas=("desktop",)`. Uma instância com `Luna(config, plataforma="web")` não as enxerga, e o comando "ajuda" lista só o que está disponível em cada plataforma.

### Criando uma habilidade

```python
# luna/habilidades/dado.py
import random
from ..core.registro import habilidade

@habilidade(r"\brolar (?:um )?dado(?: de (?P<lados>\d+) lados)?",
            descricao="Rola um dado", exemplo="Rolar um dado de 20 lados")
def rolar(ctx, lados="6"):
    ctx.dizer("dado", valor=random.randint(1, int(lados)))
    # e em personalidade.py: "dado": ["Deu {valor} 🎲", "Rolou... {valor}!"]
```

Depois, importe o módulo em `luna/habilidades/__init__.py`. A habilidade já aparece no comando "ajuda".

- Os padrões são aplicados ao comando **normalizado** (minúsculo, sem acento e sem pontuação).
- Grupos em `livres=("nome",)` chegam como o usuário falou, com acentos e maiúsculas.
- `prioridade` desempata quando dois padrões casam (maior vence).

O que uma habilidade pode usar no `ctx`:

| Método | Efeito |
|---|---|
| `ctx.dizer("chave", **valores)` | fala uma variação da personalidade |
| `ctx.falar(texto, idioma="pt")` | fala um texto livre |
| `ctx.abrir_url(url)` | ação `abrir_url` |
| `ctx.agendar(segundos, mensagem)` | ação `timer` |
| `ctx.acao(tipo, **dados)` | qualquer outra ação |
| `ctx.perguntar(texto, continuar=fn, **dados)` | faz uma pergunta; a próxima frase vai para `fn(ctx, resposta=..., **dados)`. "Deixa pra lá" cancela |

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

São 152 testes, que rodam em menos de 1 segundo, sem internet e sem tocar no sistema:

- as APIs são simuladas e cada teste usa um SQLite temporário, e um PostgREST falso em memória testa o Supabase com os filtros e headers reais;
- a API é testada de ponta a ponta com o `TestClient`, incluindo validação, CORS e fluxo de sessão;
- um teste garante que **o exemplo de cada habilidade aciona a própria habilidade**, para o "ajuda" nunca mentir;
- a CI roda no GitHub Actions a cada push, com Python 3.10 a 3.15. O front passa por typecheck, build e pelo teste E2E no Chromium, que guarda as capturas de tela como artefato.

## APIs usadas (nenhuma exige chave)

AwesomeAPI (cotações) · wttr.in (clima) · Google News RSS (notícias) · Wikipédia REST (resumos) · MyMemory, via `translate` (tradução)

## Tecnologias

Python 3.10+ · FastAPI · Pydantic · Gemini API · Supabase · React 19 · TypeScript · Vite · Web Speech API · Playwright · SpeechRecognition · PyAudio · gTTS · playsound · Beautiful Soup 4 · translate · requests · sqlite3 · threading
