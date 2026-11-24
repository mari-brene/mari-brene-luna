"""
Entrada e saída da assistente.

- ModoVoz: microfone (SpeechRecognition) + fala (gTTS + playsound).
- ModoTexto: teclado + terminal; útil para desenvolver sem microfone.
As bibliotecas de áudio só são importadas no modo voz.
"""

import os
import tempfile
import threading
import uuid

from ..core.personalidade import sem_emoji

ROXO = "\033[95m"
RESET = "\033[0m"


class ModoTexto:
    def __init__(self, nome: str):
        self.nome = nome
        self._trava = threading.Lock()  # timers falam a partir de outras threads

    def falar(self, texto: str, idioma: str = "pt") -> None:
        with self._trava:
            print(f"{ROXO}{self.nome}:{RESET} {texto}")

    def ouvir(self, pergunta: str | None = None, **_) -> str:
        if pergunta:
            self.falar(pergunta)
        try:
            return input("Você: ").strip()
        except EOFError:
            return "encerrar"


class ModoVoz(ModoTexto):
    def __init__(self, nome: str, idioma: str = "pt-BR"):
        super().__init__(nome)
        import speech_recognition as sr  # import tardio
        from gtts import gTTS
        from playsound import playsound

        self._sr, self._gTTS, self._playsound = sr, gTTS, playsound
        self.idioma = idioma
        self.reconhecedor = sr.Recognizer()
        self.reconhecedor.pause_threshold = 0.8

    def falar(self, texto: str, idioma: str = "pt") -> None:
        with self._trava:
            print(f"{ROXO}{self.nome}:{RESET} {texto}")
            caminho = os.path.join(tempfile.gettempdir(), f"luna_{uuid.uuid4().hex}.mp3")
            try:
                tld = "com.br" if idioma == "pt" else "com"
                self._gTTS(text=sem_emoji(texto), lang=idioma, tld=tld).save(caminho)
                self._playsound(caminho)
            except Exception as erro:
                print(f"  [sem áudio: {erro}]")
            finally:
                try:
                    os.remove(caminho)
                except OSError:
                    pass

    def ouvir(self, pergunta: str | None = None, tempo_limite: int = 6, idioma: str | None = None) -> str:
        if pergunta:
            self.falar(pergunta)
        sr = self._sr
        with sr.Microphone() as fonte:
            self.reconhecedor.adjust_for_ambient_noise(fonte, duration=0.4)
            try:
                audio = self.reconhecedor.listen(fonte, timeout=tempo_limite, phrase_time_limit=12)
            except sr.WaitTimeoutError:
                return ""
        try:
            texto = self.reconhecedor.recognize_google(audio, language=idioma or self.idioma)
            print(f"Você: {texto}")
            return texto
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as erro:
            print(f"  [reconhecimento indisponível: {erro}]")
            return ""
