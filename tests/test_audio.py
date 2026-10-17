"""RF02 — gravação/detecção de fala; RNF02 — microfone indisponível."""

import io
import sys
import threading
import wave

import numpy as np
import pytest

from visao_llm import audio
from visao_llm.audio import AudioPlayer, AudioRecorder, SilenceDetector, pcm16_to_wav, rms
from visao_llm.errors import MicrophoneError, NoSpeechError, SpeakerError

BLOCO = 0.05


def alimentar(det: SilenceDetector, niveis):
    for i, n in enumerate(niveis):
        if det.feed(n):
            return i
    return None


def test_detector_para_apos_silencio():
    det = SilenceDetector(block_seconds=BLOCO, silence_seconds=1.0)
    niveis = [0.002] * 6 + [0.2] * 20 + [0.002] * 40  # ruído, fala, silêncio
    parou_em = alimentar(det, niveis)
    assert det.speech_started
    assert parou_em == 6 + 20 + 20 - 1  # 1,0 s de silêncio = 20 blocos


def test_detector_sem_fala_expira():
    det = SilenceDetector(block_seconds=BLOCO, no_speech_timeout=2.0)
    parou_em = alimentar(det, [0.001] * 100)
    assert not det.speech_started
    assert parou_em == 39  # 2 s


def test_detector_tempo_maximo():
    det = SilenceDetector(block_seconds=BLOCO, max_seconds=3.0)
    assert alimentar(det, [0.3] * 200) == 59


def test_detector_ignora_ruido_de_fundo_alto():
    """Ruído ambiente constante (ventilador) não deve contar como fala."""
    det = SilenceDetector(block_seconds=BLOCO, no_speech_timeout=2.0)
    alimentar(det, [0.02] * 40)
    assert not det.speech_started


def test_rms_e_wav():
    assert rms(np.zeros(100, np.int16)) == 0
    assert rms(np.full(100, 16384, np.int16)) == pytest.approx(0.5)
    wav = pcm16_to_wav(np.zeros(16000, np.int16), 16000)
    with wave.open(io.BytesIO(wav)) as wf:
        assert (wf.getframerate(), wf.getnchannels(), wf.getnframes()) == (16000, 1, 16000)


def test_ct06_sem_biblioteca_de_audio_gera_microphone_error(monkeypatch):
    """CT06: PortAudio/sounddevice ausente -> MicrophoneError amigável."""
    monkeypatch.setitem(sys.modules, "sounddevice", None)  # força ImportError
    with pytest.raises(MicrophoneError, match="digite a pergunta"):
        AudioRecorder().record()


class FakeStream:
    def __init__(self, blocos, erro=None):
        self.blocos, self.erro = list(blocos), erro

    def __enter__(self):
        if self.erro:
            raise self.erro
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        valor = self.blocos.pop(0) if self.blocos else 0
        return np.full((n, 1), valor, np.int16), False


class FakeSD:
    def __init__(self, blocos=(), erro=None):
        self._blocos, self._erro = blocos, erro

    def InputStream(self, **kw):  # noqa: N802
        return FakeStream(self._blocos, self._erro)


def test_ct07_microfone_desconectado(monkeypatch):
    """CT07: erro do dispositivo (PortAudioError) -> MicrophoneError."""
    monkeypatch.setattr(audio, "_sounddevice", lambda: FakeSD(erro=OSError("Device unavailable")))
    with pytest.raises(MicrophoneError, match="microfone"):
        AudioRecorder().record()


def test_gravacao_completa_com_fala(monkeypatch):
    blocos = [10] * 6 + [8000] * 20 + [10] * 40
    monkeypatch.setattr(audio, "_sounddevice", lambda: FakeSD(blocos))
    niveis = []
    wav = AudioRecorder(silence_seconds=0.5).record(on_level=niveis.append)
    assert wav[:4] == b"RIFF"
    assert max(niveis) > 0.1 and niveis[-1] == 0.0


def test_ct08_silencio_total_gera_no_speech(monkeypatch):
    """CT08: usuário não falou nada -> NoSpeechError (mensagem orienta a repetir)."""
    monkeypatch.setattr(audio, "_sounddevice", lambda: FakeSD([5] * 400))
    with pytest.raises(NoSpeechError, match="Não ouvi"):
        AudioRecorder(no_speech_timeout=1.0).record()


def test_parar_manual_envia_o_que_foi_gravado(monkeypatch):
    monkeypatch.setattr(audio, "_sounddevice", lambda: FakeSD([3000] * 400))
    parar = threading.Event()
    contagem = {"n": 0}

    def nivel(_):
        contagem["n"] += 1
        if contagem["n"] == 12:
            parar.set()

    wav = AudioRecorder().record(stop_event=parar, on_level=nivel)
    assert wav[:4] == b"RIFF"


def test_player_sem_saida_de_audio(monkeypatch):
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    with pytest.raises(SpeakerError):
        AudioPlayer().play_pcm16(b"\x00\x01" * 100, 24000)
