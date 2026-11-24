# 🌙 Luna — Assistente Virtual em Python

[![testes](https://github.com/mari-brene/mari-brene-luna/actions/workflows/testes.yml/badge.svg)](https://github.com/mari-brene/mari-brene-luna/actions/workflows/testes.yml)

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

## Configuração — `config.json`

- `nome` / `palavra_ativacao`: identidade e a palavra que a desperta
- `cidade_padrao`: usada quando você pergunta só "clima"
- `pomodoro`: minutos de foco e pausa
- `programas` / `apelidos_programas`: o que ela consegue abrir, com o comando de cada sistema operacional (`Windows`, `Linux`, `Darwin`)

## Arquitetura

O **núcleo** recebe uma frase e devolve uma `Resposta` estruturada. Ele nunca fala nem executa nada sozinho. Quem decide **como** falar e **como** executar cada ação é o **cliente**: hoje o terminal, e no futuro a web.

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
  clientes/
    executor.py            executa as ações no PC (navegador, timers, programas, shutdown)
    voz.py                 ModoVoz (SpeechRecognition + gTTS) e ModoTexto
tests/                     pytest: roteamento, habilidades (APIs mockadas), sessões
dados/luna.db              lembretes (SQLite; LUNA_DB muda o caminho)
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

São 86 testes, que rodam em menos de 1 segundo, sem internet e sem tocar no sistema:

- as APIs são simuladas e cada teste usa um SQLite temporário;
- um teste garante que **o exemplo de cada habilidade aciona a própria habilidade**, para o "ajuda" nunca mentir;
- a CI roda no GitHub Actions a cada push, com Python 3.10 a 3.13.

## APIs usadas (nenhuma exige chave)

AwesomeAPI (cotações) · wttr.in (clima) · Google News RSS (notícias) · Wikipédia REST (resumos) · MyMemory, via `translate` (tradução)

## Tecnologias

Python 3.10+ · SpeechRecognition · PyAudio · gTTS · playsound · Beautiful Soup 4 · translate · requests · sqlite3 · threading
