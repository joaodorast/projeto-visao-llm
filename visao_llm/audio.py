"""Gravação do microfone (RF02) e reprodução no alto-falante (RF04).

A gravação para sozinha quando o usuário termina de falar (detecção de silêncio
por energia), quando atinge o tempo máximo, ou quando o usuário clica em "Parar".

No modo conversa, a gravação espera a fala começar pelo tempo que for preciso
(`aguardar_fala=True`) e só o trecho a partir de um pouco antes da fala é enviado.
"""

from __future__ import annotations

import io
import logging
import threading
import time
import wave
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .errors import MicrophoneError, NoSpeechError, SpeakerError

log = logging.getLogger(__name__)


def _sounddevice():
    """Importa sounddevice sob demanda: se PortAudio faltar, o app continua abrindo."""
    try:
        import sounddevice as sd  # noqa: WPS433
    except (ImportError, OSError) as exc:
        raise MicrophoneError(
            "Biblioteca de áudio indisponível (sounddevice/PortAudio). "
            "Instale as dependências do README ou digite a pergunta.",
            detalhe=str(exc),
        ) from exc
    return sd


# --------------------------------------------------------------------------- VAD
def rms(bloco: np.ndarray) -> float:
    if bloco.size == 0:
        return 0.0
    x = bloco.astype(np.float32)
    if bloco.dtype == np.int16:
        x /= 32768.0
    return float(np.sqrt(np.mean(np.square(x))))


@dataclass
class SilenceDetector:
    """Detector de fala/silêncio por energia, com calibração do ruído ambiente.

    Lógica pura (sem hardware) para poder ser testada unitariamente.
    """

    block_seconds: float
    silence_seconds: float = 1.3
    max_seconds: float = 15.0
    no_speech_timeout: float = 6.0
    calibration_seconds: float = 0.3
    min_threshold: float = 0.012
    noise_factor: float = 3.0
    #: Modo conversa: espera a fala sem limite; o tempo máximo conta a partir do início da fala.
    wait_forever: bool = False

    def __post_init__(self) -> None:
        self.elapsed = 0.0
        self.speech_elapsed = 0.0
        self.speech_started = False
        self._silence_run = 0.0
        self._noise_samples: list[float] = []
        self.threshold = self.min_threshold

    def feed(self, nivel: float) -> bool:
        """Recebe o RMS de um bloco. Retorna True quando a gravação deve parar."""
        self.elapsed += self.block_seconds
        eps = 1e-9  # evita erro de arredondamento ao somar blocos de 0,05 s

        if self.elapsed <= self.calibration_seconds + eps and not self.speech_started:
            self._noise_samples.append(nivel)
            ruido = float(np.median(self._noise_samples))
            self.threshold = max(self.min_threshold, ruido * self.noise_factor)
            # Mesmo calibrando, uma fala forte já conta
            if nivel < self.threshold * 2:
                return False

        if nivel >= self.threshold:
            self.speech_started = True
            self._silence_run = 0.0
        elif self.speech_started:
            self._silence_run += self.block_seconds
        if self.speech_started:
            self.speech_elapsed += self.block_seconds

        duracao = self.speech_elapsed if self.wait_forever else self.elapsed
        if duracao >= self.max_seconds - eps:
            return True
        if self.speech_started and self._silence_run >= self.silence_seconds - eps:
            return True
        if (not self.wait_forever and not self.speech_started
                and self.elapsed >= self.no_speech_timeout - eps):
            return True
        return False


# ------------------------------------------------------------------------ WAV
def pcm16_to_wav(pcm: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(np.asarray(pcm, dtype=np.int16).tobytes())
    return buf.getvalue()


# ------------------------------------------------------------------- gravador
PRE_FALA_SEG = 0.5  # áudio mantido antes do início da fala (não corta a primeira sílaba)


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, block_seconds: float = 0.05,
                 silence_seconds: float = 1.3, max_seconds: float = 15.0,
                 no_speech_timeout: float = 6.0, device: int | str | None = None):
        self.sample_rate = sample_rate
        self.block_seconds = block_seconds
        self.silence_seconds = silence_seconds
        self.max_seconds = max_seconds
        self.no_speech_timeout = no_speech_timeout
        self.device = device

    def check_available(self) -> str:
        """Valida se há um microfone. Retorna o nome do dispositivo."""
        sd = _sounddevice()
        try:
            info = sd.query_devices(self.device, kind="input")
        except Exception as exc:
            raise MicrophoneError("Nenhum microfone encontrado.", detalhe=str(exc)) from exc
        return str(info.get("name", "microfone"))

    def record(self, stop_event: threading.Event | None = None,
               on_level: Callable[[float], None] | None = None,
               aguardar_fala: bool = False) -> bytes:
        """Grava até detectar o fim da fala. Retorna WAV (bytes).

        Com `aguardar_fala=True` (modo conversa), espera a fala começar sem limite de tempo,
        até `stop_event`. Lança MicrophoneError (dispositivo) ou NoSpeechError (nada foi dito).
        """
        sd = _sounddevice()
        stop_event = stop_event or threading.Event()
        bloco = max(1, int(self.sample_rate * self.block_seconds))
        detector = SilenceDetector(
            block_seconds=bloco / self.sample_rate,
            silence_seconds=self.silence_seconds,
            max_seconds=self.max_seconds,
            no_speech_timeout=self.no_speech_timeout,
            wait_forever=aguardar_fala,
        )
        partes: list[np.ndarray] = []
        blocos_pre_fala = max(1, int(PRE_FALA_SEG / (bloco / self.sample_rate)))
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="int16",
                                blocksize=bloco, device=self.device) as stream:
                while not stop_event.is_set():
                    dados, _overflow = stream.read(bloco)
                    mono = dados[:, 0].copy()
                    partes.append(mono)
                    nivel = rms(mono)
                    if on_level:
                        on_level(nivel)
                    if detector.feed(nivel):
                        break
                    if not detector.speech_started and len(partes) > blocos_pre_fala:
                        del partes[0]  # antes da fala, guarda só o último meio segundo
        except MicrophoneError:
            raise
        except Exception as exc:  # PortAudioError, dispositivo removido etc.
            raise MicrophoneError(
                "Não foi possível usar o microfone. Verifique se ele está conectado "
                "e se o sistema permite o acesso.",
                detalhe=str(exc),
            ) from exc
        finally:
            if on_level:
                on_level(0.0)

        if not partes or (aguardar_fala and not detector.speech_started):
            raise NoSpeechError("Gravação cancelada.")
        audio = np.concatenate(partes)
        parado_pelo_usuario = stop_event.is_set()
        if not detector.speech_started and not parado_pelo_usuario:
            raise NoSpeechError("Não ouvi nenhuma pergunta. Clique e fale mais perto do microfone.")
        if len(audio) < self.sample_rate * 0.3:
            raise NoSpeechError("A gravação ficou curta demais. Tente novamente.")
        log.info("Áudio gravado: %.1fs", len(audio) / self.sample_rate)
        return pcm16_to_wav(audio, self.sample_rate)


# ------------------------------------------------------------------- player
class AudioPlayer:
    """Reproduz PCM 16-bit mono. Pode ser interrompido por stop()."""

    def __init__(self) -> None:
        self._stop = threading.Event()

    def play_pcm16(self, pcm: bytes, sample_rate: int) -> None:
        sd = None
        try:
            sd = _sounddevice()
            dados = np.frombuffer(pcm, dtype=np.int16)
            if dados.size == 0 or self._stop.is_set():
                return
            sd.play(dados, sample_rate)
            duracao = dados.size / sample_rate
            fim = time.monotonic() + duracao + 0.5
            while time.monotonic() < fim:
                if self._stop.is_set():
                    sd.stop()
                    return
                time.sleep(0.05)
            sd.wait()
        except MicrophoneError as exc:
            raise SpeakerError("Saída de áudio indisponível.", detalhe=exc.detalhe) from exc
        except Exception as exc:
            raise SpeakerError("Não foi possível reproduzir o áudio no alto-falante.",
                               detalhe=str(exc)) from exc

    def reset(self) -> None:
        """Chamado no início de cada fala; um stop() posterior a interrompe."""
        self._stop.clear()

    def stop(self) -> None:
        self._stop.set()
