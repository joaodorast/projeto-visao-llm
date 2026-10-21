"""Modo conversa: ouvir sem novo clique, encerrar por voz ou botão, erros sem derrubar a conversa."""

import threading

import numpy as np
import pytest

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision
from test_audio import FakeSD
from visao_llm import audio
from visao_llm.audio import AudioRecorder, SilenceDetector
from visao_llm.errors import MicrophoneError, NetworkError, NoSpeechError
from visao_llm.pipeline import Assistant, Callbacks, pedido_de_encerramento

BLOCO = 0.05


# ------------------------------------------------------- frase de encerramento
@pytest.mark.parametrize("texto", [
    "Encerrar conversa.", "Pode parar, obrigado!", "Tchau!", "Chega.", "Encerra a conversa por favor",
    "Ok, pode encerrar", "Era só isso, valeu.", "Até logo!", "Parar de ouvir", "fim", "Pare.",
])
def test_reconhece_pedidos_de_encerramento(texto):
    assert pedido_de_encerramento(texto)


@pytest.mark.parametrize("texto", [
    "Para que serve esse objeto?", "O que está escrito na placa de pare?",
    "Quanto tempo falta para o fim do jogo?", "O que tem sobre a mesa?",
    "Me diga como encerrar uma conversa difícil com alguém do trabalho",
    "Tchau é uma palavra italiana? Explique a origem dela em detalhes", "",
])
def test_perguntas_normais_nao_encerram(texto):
    assert not pedido_de_encerramento(texto)


# ------------------------------------------------------------------ gravador
def alimentar(det, niveis):
    for i, n in enumerate(niveis):
        if det.feed(n):
            return i
    return None


def test_detector_no_modo_conversa_espera_a_fala_sem_limite():
    det = SilenceDetector(block_seconds=BLOCO, no_speech_timeout=1.0, wait_forever=True)
    assert alimentar(det, [0.001] * 2000) is None  # 100 s de silêncio: continua esperando
    assert not det.speech_started


def test_tempo_maximo_conta_a_partir_do_inicio_da_fala():
    det = SilenceDetector(block_seconds=BLOCO, max_seconds=2.0, wait_forever=True)
    niveis = [0.001] * 400 + [0.5] * 100  # 20 s esperando, depois fala contínua
    parou = alimentar(det, niveis)
    assert parou is not None and 400 + 38 <= parou <= 400 + 40  # ~2 s depois de começar a falar


def test_gravacao_guarda_so_meio_segundo_antes_da_fala(monkeypatch):
    blocos = [10] * 200 + [8000] * 20 + [10] * 40  # 10 s de silêncio antes de falar
    monkeypatch.setattr(audio, "_sounddevice", lambda: FakeSD(blocos))
    wav = AudioRecorder(silence_seconds=0.5).record(aguardar_fala=True)
    import io
    import wave
    with wave.open(io.BytesIO(wav)) as wf:
        duracao = wf.getnframes() / wf.getframerate()
    assert duracao < 3.0  # não envia os 10 s de silêncio


def test_parar_enquanto_espera_a_fala_nao_envia_audio(monkeypatch):
    monkeypatch.setattr(audio, "_sounddevice", lambda: FakeSD([5] * 400))
    parar = threading.Event()
    contagem = {"n": 0}

    def nivel(_):
        contagem["n"] += 1
        if contagem["n"] == 30:
            parar.set()

    with pytest.raises(NoSpeechError):
        AudioRecorder().record(stop_event=parar, on_level=nivel, aguardar_fala=True)


# ------------------------------------------------------------------ pipeline
def montar(frame, stt, **kw):
    kw.setdefault("recorder", FakeRecorder())
    kw.setdefault("vision", FakeVision())
    kw.setdefault("speaker", FakeSpeaker())
    return Assistant(frame_provider=lambda: frame, stt=stt, **kw)


def test_conversa_responde_e_encerra_por_voz(frame):
    rec, vision, voz = FakeRecorder(), FakeVision(), FakeSpeaker()
    a = montar(frame, FakeSTT(["O que tem na mesa?", "E de que cor é a garrafa?", "Encerrar conversa"]),
               recorder=rec, vision=vision, speaker=voz)
    rodadas = []

    motivo = a.converse(threading.Event(), Callbacks(on_turn_done=lambda: rodadas.append(1)))

    assert motivo == "voz"
    assert [c[1] for c in vision.chamadas] == ["O que tem na mesa?", "E de que cor é a garrafa?"]
    assert vision.chamadas[1][2][0].pergunta == "O que tem na mesa?"  # contexto mantido
    assert rec.aguardou_fala == [True, True, True]  # sempre esperando a fala, sem clique
    assert len(rodadas) == 2
    assert "encerrando" in voz.falado[-1].lower()  # despedida falada


def test_botao_encerra_a_conversa(frame):
    parar = threading.Event()
    a = montar(frame, FakeSTT("Oi"))
    motivo = a.converse(parar, Callbacks(on_answer=lambda r: parar.set()))
    assert motivo == "botao"


def test_silencio_e_ruido_nao_encerram(frame):
    class RecorderComSilencio(FakeRecorder):
        def record(self, stop_event=None, on_level=None, aguardar_fala=False):
            self.chamadas += 1
            if self.chamadas <= 2:
                raise NoSpeechError("Gravação cancelada.")
            return b"RIFF"

    rec = RecorderComSilencio()
    a = montar(frame, FakeSTT(["Encerrar conversa"]), recorder=rec)
    assert a.converse(threading.Event(), Callbacks()) == "voz"
    assert rec.chamadas == 3


def test_erro_de_rede_avisa_e_a_conversa_continua(frame):
    class VisaoInstavel(FakeVision):
        def ask(self, jpeg, pergunta, historico=()):
            self.chamadas.append((jpeg, pergunta, tuple(historico)))
            if len(self.chamadas) == 1:
                raise NetworkError("Sem conexão com a API.")
            return "Agora deu certo."

    erros, respostas = [], []
    a = montar(frame, FakeSTT(["Primeira?", "Segunda?", "Tchau"]), vision=VisaoInstavel())
    cb = Callbacks(on_error=lambda e: erros.append(e.mensagem),
                   on_answer=lambda r: respostas.append(r.resposta))
    assert a.converse(threading.Event(), cb) == "voz"
    assert erros == ["Sem conexão com a API."]
    assert respostas == ["Agora deu certo."]


def test_sem_microfone_a_conversa_termina_com_erro(frame):
    a = montar(frame, FakeSTT("Oi"), recorder=FakeRecorder(erro=MicrophoneError("Sem microfone.")))
    with pytest.raises(MicrophoneError):
        a.converse(threading.Event(), Callbacks())


def test_pedido_de_encerramento_so_vale_no_modo_conversa(frame):
    vision = FakeVision()
    a = montar(frame, FakeSTT("Tchau"), vision=vision)
    a.ask_by_voice()  # pergunta avulsa: "tchau" vai para o modelo normalmente
    assert vision.chamadas[-1][1] == "Tchau"


# ----------------------------------------------------------------- interface
PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication  # noqa: E402

from test_gui import esperar  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui.main_window import TEXTO_CONVERSA, TEXTO_ENCERRAR, TEXTO_MIC, MainWindow  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402
from visao_llm.history import HistoryStore  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


class RecorderLento(FakeRecorder):
    """Simula a espera pela fala, para dar tempo de clicar em Encerrar."""

    def record(self, stop_event=None, on_level=None, aguardar_fala=False):
        if stop_event is not None and stop_event.wait(0.3):
            raise NoSpeechError("Gravação cancelada.")
        return super().record(stop_event, on_level, aguardar_fala)


def janela(tmp_path, imagem, stt, continua=True, recorder=None):
    fakes = {"vision": FakeVision(), "recorder": recorder or FakeRecorder()}
    cfg = Config(api_key="k", camera_source=str(imagem), history_dir=tmp_path,
                 continuous_conversation=continua)
    w = MainWindow(cfg, lambda f, p: Assistant(frame_provider=f, recorder=fakes["recorder"],
                                               stt=stt, vision=fakes["vision"],
                                               speaker=FakeSpeaker(),
                                               store=HistoryStore(tmp_path)))
    w.fakes = fakes
    w.show()
    return w


def test_um_clique_conversa_ate_o_pedido_de_encerramento(app, tmp_path, imagem_teste):
    w = janela(tmp_path, imagem_teste, FakeSTT(["O que tem na mesa?", "E a garrafa?", "Encerrar conversa"]))
    try:
        assert esperar(app, w.live_view.has_image)
        assert w.mic_button.text() == TEXTO_CONVERSA
        w.mic_button.click()  # um único clique
        assert w._conversa_ativa and w.conversation_hint.isVisibleTo(w)
        assert esperar(app, lambda: not w._conversa_ativa, 5)
        assert w.history.count() == 2
        assert w.mic_button.text() == TEXTO_CONVERSA and w.mic_button.isEnabled()
        assert not w.conversation_hint.isVisibleTo(w)
        assert "a seu pedido" in w.statusBar().currentMessage()
        assert len(HistoryStore(tmp_path).load()) == 2
    finally:
        w.close()


def test_botao_encerrar_termina_a_conversa(app, tmp_path, imagem_teste):
    w = janela(tmp_path, imagem_teste, FakeSTT("Oi"), recorder=RecorderLento())
    try:
        assert esperar(app, w.live_view.has_image)
        w.mic_button.click()
        assert esperar(app, lambda: w.mic_button.text() == TEXTO_ENCERRAR, 3)
        w.mic_button.click()
        assert esperar(app, lambda: not w._conversa_ativa, 5)
        assert w.mic_button.text() == TEXTO_CONVERSA and not w.busy
    finally:
        w.close()


def test_esc_ouvindo_encerra_a_conversa(app, tmp_path, imagem_teste):
    w = janela(tmp_path, imagem_teste, FakeSTT("Oi"), recorder=RecorderLento())
    try:
        assert esperar(app, w.live_view.has_image)
        w.mic_button.click()
        assert esperar(app, lambda: w._estado == "OUVINDO", 3)
        w._on_escape()
        assert esperar(app, lambda: not w._conversa_ativa, 5)
    finally:
        w.close()


def test_sem_conversa_continua_o_botao_faz_uma_pergunta(app, tmp_path, imagem_teste):
    w = janela(tmp_path, imagem_teste, FakeSTT("O que tem na mesa?"), continua=False)
    try:
        assert esperar(app, w.live_view.has_image)
        assert w.mic_button.text() == TEXTO_MIC
        w.mic_button.click()
        assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO", 5)
        assert w.history.count() == 1 and not w._conversa_ativa
        assert w.fakes["recorder"].aguardou_fala == [False]
    finally:
        w.close()
