"""RF05/RNF02/RNF03 — interface: estados, falhas exibidas e responsividade.

Roda com QT_QPA_PLATFORM=offscreen (sem monitor).
"""

import time

import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.errors import ConfigError, NetworkError  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402
from visao_llm.pipeline import Assistant  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


def esperar(app, condicao, timeout=5.0):
    fim = time.monotonic() + timeout
    while time.monotonic() < fim:
        app.processEvents()
        if condicao():
            return True
        time.sleep(0.01)
    return False


def fabrica(vision=None, speaker=None):
    def criar(frames, player):
        return Assistant(frame_provider=frames, recorder=FakeRecorder(), stt=FakeSTT(),
                         vision=vision or FakeVision(), speaker=speaker or FakeSpeaker())
    return criar


def janela(app, fonte, factory):
    w = MainWindow(Config(api_key="sk-teste", camera_source=fonte, save_history=False), factory)
    w.show()
    return w


def test_ct21_interface_mostra_imagem_pergunta_e_resposta(app, imagem_teste):
    """CT21: após a pergunta, a GUI mostra imagem capturada, pergunta e resposta (RF04/RF05)."""
    w = janela(app, str(imagem_teste), fabrica())
    try:
        assert esperar(app, w.live_view.has_image), "câmera ao vivo não exibiu frame"
        assert "ao vivo" in w.cam_badge.text()
        w._start(None)  # mesmo efeito do botão "Clique para falar"
        assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO")
        assert w.captured_view.has_image()
        assert w.question_label.text() == "O que está sobre a mesa?"
        assert w.answer_label.text() == "Vejo um notebook e uma garrafa sobre a mesa."
        assert w.history.count() == 1
        assert w.mic_button.isEnabled() and w.repeat_button.isEnabled()
        assert not w.error_banner.isVisible()
    finally:
        w.close()


def test_ct22_camera_indisponivel_na_interface(app):
    """CT22: sem câmera, a GUI avisa, não fecha e mostra erro ao perguntar."""
    w = janela(app, 97, fabrica())
    try:
        assert esperar(app, lambda: "sem sinal" in w.cam_badge.text())
        w.text_input.setText("O que você vê?")
        w._on_send_text()
        assert esperar(app, lambda: not w.busy and w.error_banner.isVisible())
        assert "Câmera" in w.error_banner.text()
        assert w._estado == "ERRO" and w.mic_button.isEnabled()
    finally:
        w.close()


def test_ct23_falha_de_conexao_na_interface(app, imagem_teste):
    """CT23: rede caída -> banner de erro de conexão; app continua utilizável."""
    w = janela(app, str(imagem_teste), fabrica(vision=FakeVision(erro=NetworkError(
        "Sem conexão com a OpenAI ao consultar o modelo de visão."))))
    try:
        assert esperar(app, w.live_view.has_image)
        w._start("teste")
        assert esperar(app, lambda: not w.busy and w.error_banner.isVisible())
        assert "Conexão" in w.error_banner.text()
        assert w.send_button.isEnabled()
    finally:
        w.close()


def test_ct24_sem_chave_api_na_interface(app, imagem_teste):
    """CT24: chave ausente -> mensagem de configuração, sem travar."""
    def sem_chave(frames, player):
        raise ConfigError("Chave da OpenAI não configurada.")

    w = janela(app, str(imagem_teste), sem_chave)
    try:
        w._start(None)
        assert w.error_banner.isVisible() and "Configuração" in w.error_banner.text()
        assert not w.busy
    finally:
        w.close()


def test_ct25_interface_responsiva_durante_chamada(app, imagem_teste):
    """CT25 (RNF03): enquanto a API demora 1,5 s, o loop de eventos da GUI segue rodando."""
    class VisaoLenta(FakeVision):
        def ask(self, *a, **k):
            time.sleep(1.5)
            return super().ask(*a, **k)

    w = janela(app, str(imagem_teste), fabrica(vision=VisaoLenta()))
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    try:
        assert esperar(app, w.live_view.has_image)
        timer.start(50)
        w._start("demora?")
        assert esperar(app, lambda: w._estado == "PROCESSANDO", 2)
        assert not w.mic_button.isEnabled()  # estado "processando" visível
        assert esperar(app, lambda: not w.busy, 5)
        timer.stop()
        assert len(ticks) >= 15, f"GUI travou: só {len(ticks)} ticks em ~1,5 s"
        maior_intervalo = max(b - a for a, b in zip(ticks, ticks[1:]))
        assert maior_intervalo < 0.5
    finally:
        w.close()


def test_aviso_quando_voz_falha(app, imagem_teste):
    w = janela(app, str(imagem_teste), fabrica(speaker=FakeSpeaker(falhar=True)))
    try:
        assert esperar(app, w.live_view.has_image)
        w._start("oi")
        assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO")
        assert w.warn_banner.isVisible() and "não falada" in w.warn_banner.text()
        assert w.answer_label.text()
    finally:
        w.close()
