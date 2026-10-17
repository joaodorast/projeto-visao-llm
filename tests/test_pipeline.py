"""Fluxo completo (itens 1–6 do enunciado) com dublês, incluindo cenários de falha."""

import json
import threading

import numpy as np
import pytest

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision, camera_quebrada
from visao_llm.errors import (APIError, AppError, CameraError, MicrophoneError, NetworkError,
                              SpeakerError)
from visao_llm.history import HistoryStore
from visao_llm.pipeline import Assistant, Callbacks
from visao_llm.speaker import Speaker


def montar(frame, **kw):
    base = dict(frame_provider=lambda: frame, recorder=FakeRecorder(), stt=FakeSTT(),
                vision=FakeVision(), speaker=FakeSpeaker())
    base.update(kw)
    return Assistant(**base)


def gravar_eventos():
    eventos = []
    cb = Callbacks(
        on_state=lambda s, d: eventos.append(("estado", s.name)),
        on_captured=lambda f: eventos.append(("imagem", f.shape)),
        on_question=lambda q: eventos.append(("pergunta", q)),
        on_answer=lambda r: eventos.append(("resposta", r.resposta)),
    )
    return eventos, cb


def test_ct15_fluxo_de_voz_completo(frame, tmp_path):
    """CT15: voz -> imagem -> STT -> LLM -> exibição -> fala, na ordem correta."""
    store = HistoryStore(tmp_path)
    a = montar(frame, store=store)
    eventos, cb = gravar_eventos()

    r = a.ask_by_voice(threading.Event(), cb)

    assert r.pergunta == "O que está sobre a mesa?"
    assert r.resposta == "Vejo um notebook e uma garrafa sobre a mesa."
    assert r.image_jpeg[:2] == b"\xff\xd8"
    assert a.speaker.falado == [r.resposta]
    assert eventos == [
        ("estado", "OUVINDO"), ("estado", "CAPTURANDO"), ("imagem", (480, 640, 3)),
        ("estado", "TRANSCREVENDO"), ("pergunta", "O que está sobre a mesa?"),
        ("estado", "PROCESSANDO"), ("resposta", r.resposta),
        ("estado", "FALANDO"), ("estado", "CONCLUIDO"),
    ]
    assert set(r.tempos) == {"gravacao", "captura", "stt", "llm", "tts"}
    # histórico em disco
    linhas = (tmp_path / "interacoes.jsonl").read_text(encoding="utf-8").splitlines()
    reg = json.loads(linhas[0])
    assert reg["pergunta"] == r.pergunta and (tmp_path / reg["imagem"]).exists()


def test_imagem_capturada_no_momento_da_pergunta(frame):
    """A foto é tirada depois que o usuário termina de falar (não antes)."""
    ordem = []

    class Rec(FakeRecorder):
        def record(self, stop_event=None, on_level=None):
            ordem.append("gravou")
            return b"wav"

    def provider():
        ordem.append("capturou")
        return frame

    montar(frame, recorder=Rec(), frame_provider=provider).ask_by_voice()
    assert ordem == ["gravou", "capturou"]


def test_ct16_fluxo_por_texto(frame):
    """CT16: pergunta digitada pula gravação e STT."""
    a = montar(frame)
    eventos, cb = gravar_eventos()
    r = a.ask_by_text("  Quantos objetos há?  ", cb)
    assert r.pergunta == "Quantos objetos há?" and r.origem == "texto"
    assert ("estado", "OUVINDO") not in eventos and a.recorder.chamadas == 0


def test_ct17_camera_indisponivel_nao_chama_api(frame):
    """CT17: câmera desconectada -> CameraError, estado ERRO e nenhuma chamada paga à API."""
    vision = FakeVision()
    a = montar(frame, frame_provider=camera_quebrada, vision=vision)
    eventos, cb = gravar_eventos()
    with pytest.raises(CameraError):
        a.ask_by_voice(cb=cb)
    assert eventos[-1] == ("estado", "ERRO")
    assert vision.chamadas == []


def test_camera_devolve_frame_vazio(frame):
    a = montar(frame, frame_provider=lambda: np.empty((0, 0, 3), np.uint8))
    with pytest.raises(CameraError):
        a.ask_by_text("oi")


def test_camera_com_excecao_desconhecida(frame):
    def explode():
        raise RuntimeError("driver travou")

    with pytest.raises(CameraError, match="Falha ao capturar"):
        montar(frame, frame_provider=explode).ask_by_text("oi")


def test_ct18_sem_conexao_na_consulta(frame):
    """CT18: falha de rede na consulta -> NetworkError, estado ERRO, app segue vivo."""
    a = montar(frame, vision=FakeVision(erro=NetworkError("Sem conexão")))
    eventos, cb = gravar_eventos()
    with pytest.raises(NetworkError):
        a.ask_by_voice(cb=cb)
    assert eventos[-1] == ("estado", "ERRO")
    # depois que a rede volta, a próxima pergunta funciona normalmente
    a.vision = FakeVision()
    assert a.ask_by_text("e agora?").resposta


def test_falha_no_microfone(frame):
    a = montar(frame, recorder=FakeRecorder(erro=MicrophoneError("sem microfone")))
    with pytest.raises(MicrophoneError):
        a.ask_by_voice()


def test_falha_na_transcricao(frame):
    a = montar(frame, stt=FakeSTT(erro=APIError("Limite de uso")))
    with pytest.raises(APIError):
        a.ask_by_voice()


def test_ct19_falha_na_voz_nao_perde_resposta(frame):
    """CT19: alto-falante/TTS falhou -> resposta continua exibida, com aviso."""
    a = montar(frame, speaker=FakeSpeaker(falhar=True))
    eventos, cb = gravar_eventos()
    r = a.ask_by_voice(cb=cb)
    assert r.resposta and r.aviso_voz == "Alto-falante desconectado."
    assert eventos[-1] == ("estado", "CONCLUIDO")


def test_pergunta_vazia(frame):
    with pytest.raises(AppError, match="Digite"):
        montar(frame).ask_by_text("   ")


def test_erro_inesperado_e_embrulhado(frame):
    a = montar(frame, vision=FakeVision(erro=ZeroDivisionError()))
    eventos, cb = gravar_eventos()
    with pytest.raises(AppError, match="inesperado"):
        a.ask_by_text("oi", cb)
    assert eventos[-1] == ("estado", "ERRO")


def test_contexto_de_conversa(frame):
    """As perguntas seguintes recebem as trocas anteriores como contexto."""
    vision = FakeVision()
    a = montar(frame, vision=vision)
    a.ask_by_text("O que tem na mesa?")
    a.ask_by_text("De que cor é a garrafa?")
    assert vision.chamadas[1][2][0].pergunta == "O que tem na mesa?"
    a.clear_context()
    a.ask_by_text("oi")
    assert vision.chamadas[2][2] == ()


def test_sem_voz_configurada(frame):
    a = montar(frame, speaker=None)
    assert a.ask_by_text("oi").aviso_voz is None


# ------------------------------------------------------------ Speaker
class TTSFake:
    def __init__(self, erro=None):
        self.erro = erro

    def synthesize(self, texto):
        if self.erro:
            raise self.erro
        return b"\x00\x00" * 10


class PlayerFake:
    def __init__(self):
        self.tocado = []

    def play_pcm16(self, pcm, sr):
        self.tocado.append((len(pcm), sr))

    def stop(self):
        pass


class OfflineFake:
    def __init__(self, falhar=False):
        self.falhar, self.falado = falhar, []

    def speak(self, texto):
        if self.falhar:
            raise SpeakerError("sem voz offline")
        self.falado.append(texto)


def test_speaker_usa_openai():
    player = PlayerFake()
    assert Speaker(TTSFake(), player, OfflineFake()).speak("oi") == "openai"
    assert player.tocado == [(20, 24000)]


def test_ct20_speaker_cai_para_voz_offline_sem_internet():
    """CT20: sem internet, a resposta é falada pela voz offline (pyttsx3)."""
    offline = OfflineFake()
    s = Speaker(TTSFake(NetworkError("Sem conexão")), PlayerFake(), offline)
    assert s.speak("oi") == "offline" and offline.falado == ["oi"]


def test_speaker_sem_nenhuma_voz():
    s = Speaker(TTSFake(NetworkError("Sem conexão")), PlayerFake(), OfflineFake(falhar=True))
    with pytest.raises(SpeakerError, match="Sem conexão"):
        s.speak("oi")


def test_historico_falha_silenciosa(frame, tmp_path):
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x")  # pasta de histórico é um arquivo -> não dá para criar
    a = montar(frame, store=HistoryStore(arquivo))
    assert a.ask_by_text("oi").resposta  # não quebra
