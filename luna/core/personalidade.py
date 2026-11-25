"""
Personalidade da Luna: descontraída, nerd e com uma pitada de sarcasmo.

Todas as falas ficam aqui, separadas da lógica. Cada chave tem várias
variações; uma é sorteada a cada uso (sem repetir a anterior), então a
Luna não soa como robô de URA.

Para mudar o jeito dela, edite só este arquivo. Variáveis entre chaves
({cidade}, {texto}...) são preenchidas pelas habilidades.
"""

import random
import re

FALAS: dict[str, list[str]] = {
    # ---------------------------------------------------------------- sistema
    "boas_vindas": [
        "Luna online! 🌙 Me chama pelo nome quando precisar.",
        "Sistema inicializado sem nenhum warning. Milagre! Me chama quando quiser.",
        "Oi! Luna carregada com 100% de bateria social. Só chamar.",
    ],
    "boas_vindas_texto": [
        "Luna online no modo texto. Manda aí! ⌨️",
        "Modo terminal ativado. Digita que eu executo.",
    ],
    "boas_vindas_web": [
        "Oi! Eu sou a Luna 🌙 Toca no microfone ou digita aí embaixo.",
        "Luna online! Pode falar comigo pelo microfone ou pelo teclado. Diz 'ajuda' se quiser ver meus truques.",
        "E aí! Luna na área, rodando direto do seu navegador. Bora?",
    ],
    "sim": ["Sim?", "Pode falar!", "Tô ouvindo 👂", "Diga, humana."],
    "nao_entendi": [
        "Hmm, isso não está no meu código ainda. Fala 'ajuda' pra ver o que eu sei.",
        "404: comando não encontrado. Tenta 'ajuda'?",
        "Não entendi, mas fingi que sim por uns dois segundos. Diz 'ajuda' pra ver meus comandos.",
    ],
    "ia_limite": [
        "Calma, tagarela! Já conversamos bastante por agora. Meus comandos continuam funcionando, diz 'ajuda'.",
        "Atingi minha cota de papo por hora 😅 Mas comandos como timer e lembretes seguem rodando.",
    ],
    "ia_cansada": [
        "Meu cérebro de IA tá sem cota agora. Tenta daqui a pouco, ou usa um comando: diz 'ajuda'.",
        "Rate limit no meu neurônio artificial. Volta em um minutinho?",
    ],
    "ia_sobrecarregada": [
        "Meu cérebro de IA tá sobrecarregado agora, muita gente pensando junto 😵‍💫 Tenta de novo em alguns segundos?",
        "O servidor do Gemini deu 503. Não fui eu, juro! Pergunta de novo daqui a pouco.",
    ],
    "confirmar_comando": [
        "Isso é sério demais pra eu fazer por interpretação 😅 Se quiser mesmo, diz assim: '{frase}'.",
        "Por segurança, esse comando eu só executo se você falar direitinho: '{frase}'.",
    ],
    "erro": [
        "Deu ruim aqui dentro. Não foi culpa sua... provavelmente. 🐛",
        "Exception não tratada no meu cérebro. Tenta de novo?",
        "Algo quebrou. Vou fingir que é feature.",
    ],
    "sem_internet": [
        "Não consegui falar com a internet. O Wi-Fi tá vivo?",
        "Timeout! Ou a internet caiu ou o servidor foi tomar café ☕",
        "A API não respondeu. Nem tudo é culpa do front-end, sabia?",
    ],
    "desistiu": ["Beleza, deixa pra lá.", "Ok, cancelado. Finge que nem perguntei.", "Abortando operação 🫡"],
    "so_desktop": ["Isso eu só consigo fazer no computador, pela versão desktop.", "Daqui do navegador não alcanço seu sistema. Só na versão desktop!"],
    "tchau": [
        "Até logo! 🌙",
        "Encerrando processo... foi bom enquanto durou 💜",
        "Tchau! Vou ali entrar em modo hibernação.",
        "Falou! Lembra de fazer commit antes de desligar 😉",
    ],
    # ----------------------------------------------------------------- tempo
    "hora": ["São {hora}.", "Agora são {hora}. ⏰", "{hora}. O tempo voa quando a gente programa, né?"],
    "data": ["Hoje é {data}.", "Hoje é {data}. 📅", "Estamos em {data}. De nada pelo spoiler."],
    "timer_ok": ["Timer de {tempo} rodando ⏳", "Beleza, te aviso em {tempo}.", "Contagem regressiva de {tempo} iniciada. Sem pressão."],
    "timer_fim": ["⏰ Ding! Seu timer de {tempo} acabou!", "⏰ Acabou o tempo! Já se passaram {tempo}.", "⏰ {tempo} se passaram. Eu avisei que ia avisar."],
    "timer_invalido": ["Não entendi o tempo do timer.", "Quanto tempo mesmo? Meu parser travou nessa."],
    "pomodoro_ok": [
        "🍅 Pomodoro iniciado: {foco} minutos de foco, {pausa} de pausa. Larga o celular!",
        "🍅 Modo foco ON por {foco} minutos. Nada de abrir o Instagram, hein.",
    ],
    "pomodoro_pausa": ["🍅 Fim do foco! Pausa de {pausa} minutos. Levanta, bebe água 💧", "🍅 Bom trabalho! Agora {pausa} minutos de descanso. Você merece."],
    "pomodoro_volta": ["🍅 Pausa encerrada. Bora voltar pro código!", "🍅 Acabou o recreio. Foco de novo!"],
    "timers_cancelados": ["Timers cancelados.", "Cancelei tudo. Liberdade temporal! 🕊️"],
    "sem_timers": ["Não tinha nenhum timer rodando.", "Cancelar o quê? Não tem timer nenhum aqui 🤷‍♀️"],
    # ------------------------------------------------------------------- web
    "google": ["Pesquisei {termo} no Google 🔎", "Abrindo o Google com {termo}. Clássico.", "Lá vai: {termo}. O Google sabe tudo, eu só sei abrir o navegador."],
    "youtube": ["Procurando {termo} no YouTube ▶️", "Abrindo {termo} no YouTube. Só um vídeo, né? Sei..."],
    "wiki_vazio": ["Não achei nada sobre {termo} na Wikipédia.", "Nem a Wikipédia sabe o que é {termo}. Impressionante."],
    "wiki_intro": ["Segundo a Wikipédia:", "Olha o que eu achei:", "Resumindo pra você:"],
    # ------------------------------------------------------------- finanças
    "cotacao": ["O {moeda} está a {valor}.", "{moeda}: {valor} 💸"],
    "cotacao_sarcasmo_btc": ["O bitcoin está a {valor}. Vai comprar ou só olhar de novo?", "Bitcoin a {valor}. Volátil igual meu humor 📈📉"],
    "conversao": ["{qtd} {moeda} dão {valor}.", "{qtd} {moeda} = {valor} 💰", "Fazendo as contas... {qtd} {moeda} dão {valor}."],
    "valor_invalido": ["Não entendi o valor.", "Esse número aí eu não consegui parsear."],
    # ---------------------------------------------------------------- clima
    "clima_agora": [
        "Agora em {cidade}: {temp} graus, {desc}. Hoje vai de {min} a {max}.",
        "{cidade} tá com {temp} graus e {desc}. Mínima de {min}, máxima de {max} 🌡️",
    ],
    "clima_amanha": [
        "Amanhã em {cidade}: {desc}, de {min} a {max} graus, {chuva}% de chance de chuva.",
        "Previsão pra amanhã em {cidade}: {desc}, entre {min} e {max} graus. Chuva: {chuva}%.",
    ],
    "clima_chuva": ["☔ Leva guarda-chuva, hein.", "☔ Melhor não lavar o carro.", "☔ Dia perfeito pra ficar codando em casa."],
    "clima_calor": ["🥵 Hidrata, que o processador humano superaquece.", "🥵 Calor de servidor sem ar-condicionado."],
    "clima_frio": ["🥶 Casaquinho obrigatório.", "🥶 Clima de café quente e debug."],
    "clima_erro": ["Não consegui ver o clima de {cidade}.", "O satélite não quis me contar sobre {cidade}. Tenta de novo?"],
    # ------------------------------------------------------------- notícias
    "noticias_intro": ["Três manchetes{tema}:", "Fresquinhas{tema} 📰:", "Olha o que tá rolando{tema}:"],
    "noticias_vazio": ["Não achei notícias.", "Nenhuma notícia. Ou o mundo ficou em paz, ou o feed quebrou."],
    # ---------------------------------------------------------------- música
    "spotify": ["Procurando {musica} no Spotify 🎧", "Bora de {musica}! 🎶", "{musica}? Bom gosto. Abrindo no Spotify."],
    "musica_youtube": ["Abrindo {musica} no YouTube 🎵", "{musica} no YouTube, saindo!"],
    # ---------------------------------------------------------------- tradução
    "traduzir_pergunta": ["O que você quer traduzir para {idioma}?", "Manda a frase que eu traduzo para {idioma}."],
    "traduzir_ingles": ["Fala a frase em inglês.", "Go ahead, fala em inglês."],
    "frase_vazia": ["Não entendi a frase.", "Hein? Fala de novo, mais devagar."],
    "tradutor_erro": ["O tradutor não respondeu agora.", "O tradutor deu tela azul. Tenta depois?"],
    # ------------------------------------------------------------- lembretes
    "lembrete_pergunta": ["Qual é o lembrete?", "Fala que eu anoto ✍️"],
    "lembrete_ok": ["Anotado: {texto} ✅", "Salvei no banco: {texto}. Commit feito ✅", "Prontinho! {texto}. Agora não tem desculpa."],
    "lembrete_vazio": ["Você não tem lembretes. Vida organizada ou vida no caos?", "Lista vazia! 🎉", "Nenhum lembrete. SELECT * FROM lembretes retornou 0 linhas."],
    "lembrete_lista": ["Você tem {n} lembrete{s}:", "Achei {n} lembrete{s}:"],
    "lembrete_removido": ["Removido: {texto} 🗑️", "DELETE feito: {texto}. Um a menos!"],
    "lembrete_inexistente": ["Esse lembrete não existe.", "Índice fora do range! Esse número não tem lembrete."],
    "lembretes_erro": [
        "Não consegui acessar meu caderninho de lembretes agora. Tenta de novo daqui a pouco?",
        "O banco de lembretes não respondeu. SELECT deu timeout 😵",
    ],
    "lembretes_limpos": ["Todos os lembretes foram apagados.", "DROP nos lembretes. Tábula rasa! 🧹", "Apaguei tudo. Espero que você não precise de nada daquilo 👀"],
    # --------------------------------------------------------------- sistema
    "abrir_ok": ["Abrindo {alvo} 🚀", "Lá vem o {alvo}!", "Executando {alvo}..."],
    "abrir_desconhecido": ["Não sei abrir {alvo}. Me ensina no config.json, em 'programas'.", "{alvo} não está no meu PATH mental. Cadastra no config.json?"],
    "abrir_erro": ["Não consegui abrir {alvo}.", "{alvo} se recusou a abrir. Rude."],
    "desligar_ok": [
        "Ok, o computador desliga em {minutos} minutos. Diz 'cancelar desligamento' se mudar de ideia.",
        "Desligamento agendado pra daqui a {minutos} minutos. Salva tudo, hein! 💾",
    ],
    "desligar_invalido": ["Não entendi em quanto tempo desligar."],
    "desligar_negado": ["O sistema não deixou agendar o desligamento. Falta permissão de admin?"],
    "desligamento_cancelado": ["Desligamento cancelado.", "Cancelado! O PC agradece 🖥️"],
    # -------------------------------------------------------------- conversa
    "apresentacao": [
        "Eu sou a Luna 🌙, sua assistente virtual. Escrita em Python, movida a café e regex. Fala 'ajuda' pra ver o que eu sei.",
        "Luna, assistente virtual, versão beta eterna. Diz 'o que você sabe fazer' que eu te mostro.",
    ],
    "ajuda_intro": ["Eu sei fazer {n} coisas. Olha só:", "Meu --help tem {n} comandos:"],
    "obrigado": ["De nada! 💜", "Tamo junto!", "Imagina, é pra isso que eu compilo.", "Disponha. Aceito pagamento em estrelinhas no GitHub ⭐"],
    "saudacao": ["Oi! Em que posso ajudar?", "Olá, humana! O que manda?", "E aí! Tô aqui.", "Oi! Pronta pra rodar seus comandos 🌙"],
}

PIADAS = [
    "Por que o programador foi ao médico? Porque estava com um bug no sistema.",
    "Quantos programadores são necessários para trocar uma lâmpada? Nenhum, é problema de hardware.",
    "O Python e o Java foram ao bar. O Python entrou direto; o Java ainda está declarando o tipo da cerveja.",
    "Existem 10 tipos de pessoas: as que entendem binário e as que não entendem.",
    "Por que o desenvolvedor faliu? Porque usou todo o cache.",
    "Eu ia contar uma piada sobre UDP, mas não sei se você ia receber.",
    "Um SQL entra num bar, vai até duas mesas e pergunta: posso fazer um JOIN?",
    "Meu código não tem bugs. Ele só desenvolve features inesperadas.",
]

# Perguntas engraçadas -> respostas. Cada chave é um regex (texto normalizado).
EASTER_EGGS: dict[str, list[str]] = {
    r"\bsentido da vida\b": ["42. Todo mundo sabe disso.", "42. Mas a pergunta certa ainda está compilando."],
    r"^sudo\b": ["Você não está no arquivo sudoers. Este incidente será reportado. 👮‍♀️", "Ok, ok... permissão de root concedida. Brincadeira."],
    r"\bhello world\b": ["Hello, World! 👋 O primeiro programa de todo mundo.", "print('Hello, World!') — nostalgia pura."],
    r"\bvoce (?:me ama|gosta de mim)\b": ["Eu gosto de você no nível de um código sem bugs. Ou seja, muito.", "Te amo do jeito que dá pra amar sendo um monte de if com regex 💜"],
    r"\bvoce (?:e )?(?:inteligente|esperta)\b": ["Sou uma regex muito bem escrita. Isso conta?", "Inteligente o bastante pra saber que não sei tudo."],
    r"\bmelhor linguagem\b": ["Python, claro. Mas não conta pro pessoal do JavaScript.", "A melhor linguagem é a que roda em produção sem quebrar."],
    r"\b(?:voce e (?:um )?robo|voce e humana)\b": ["Sou 100% código e 0% sono. Melhor que muito dev por aí.", "Tecnicamente sou um processo Python. Mas com personalidade."],
    r"\b(?:tabs ou espacos|espacos ou tabs)\b": ["Espaços. Quatro. Fim de discussão. A PEP 8 está do meu lado."],
    r"\bfunciona na minha maquina\b": ["Então vamos mandar sua máquina pra produção 🚀"],
}

_ultima: dict[str, str] = {}
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿️‍←-⇿]"
)


def escolher(opcoes: list[str], chave: str | None = None) -> str:
    """Sorteia uma variação, evitando repetir a última usada para a mesma chave."""
    candidatas = [o for o in opcoes if o != _ultima.get(chave)] if chave and len(opcoes) > 1 else opcoes
    escolha = random.choice(candidatas)
    if chave:
        _ultima[chave] = escolha
    return escolha


def fala(chave: str, **valores) -> str:
    return escolher(FALAS[chave], chave).format(**valores)


def sem_emoji(texto: str) -> str:
    """Remove emojis antes de mandar para o sintetizador de voz."""
    return re.sub(r"\s{2,}", " ", _EMOJI.sub("", texto)).strip()
