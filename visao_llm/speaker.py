"""Fala a resposta: TTS da OpenAI + alto-falante, com fallback de voz offline."""

from __future__ import annotations

import logging
import threading

from .audio import AudioPlayer
from .errors import AppError, SpeakerError
from .openai_service import TTS_SAMPLE_RATE, TextToSpeech

log = logging.getLogger(__name__)


class OfflineVoice:
    """Voz local via pyttsx3 (opcional). Usada se a TTS da OpenAI falhar."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def speak(self, texto: str) -> None:
        try:
            import pyttsx3  # noqa: WPS433
        except ImportError as exc:
            raise SpeakerError("Voz offline indisponível (pyttsx3 não instalado).") from exc
        with self._lock:
            try:
                engine = pyttsx3.init()
                for voz in engine.getProperty("voices") or []:
                    ident = f"{getattr(voz, 'id', '')} {getattr(voz, 'name', '')}".lower()
                    if "pt" in ident or "portug" in ident or "brazil" in ident:
                        engine.setProperty("voice", voz.id)
                        break
                engine.say(texto)
                engine.runAndWait()
                engine.stop()
            except Exception as exc:
                raise SpeakerError("Falha na voz offline.", detalhe=str(exc)) from exc


class Speaker:
    def __init__(self, tts: TextToSpeech | None, player: AudioPlayer | None = None,
                 offline: OfflineVoice | None = None):
        self.tts = tts
        self.player = player or AudioPlayer()
        self.offline = offline

    def speak(self, texto: str) -> str:
        """Fala o texto. Retorna o mecanismo usado ('openai' ou 'offline').

        Lança SpeakerError se nenhum mecanismo funcionar.
        """
        erro_online: AppError | None = None
        if hasattr(self.player, "reset"):
            self.player.reset()
        if self.tts is not None:
            try:
                pcm = self.tts.synthesize(texto)
                self.player.play_pcm16(pcm, TTS_SAMPLE_RATE)
                return "openai"
            except AppError as exc:
                erro_online = exc
                log.warning("TTS online falhou: %s", exc.mensagem)

        if self.offline is not None:
            try:
                self.offline.speak(texto)
                return "offline"
            except AppError as exc:
                log.warning("Voz offline falhou: %s", exc.mensagem)

        msg = erro_online.mensagem if erro_online else "Nenhum mecanismo de voz disponível."
        raise SpeakerError(f"Não foi possível falar a resposta: {msg}")

    def stop(self) -> None:
        self.player.stop()
