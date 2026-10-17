"""Navegação entre páginas, tela cheia (F11/Esc) e página de Ajuda."""

import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from test_gui import esperar  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui.help_page import ATALHOS  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402
from visao_llm.pipeline import Assistant  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


@pytest.fixture
def w(app, tmp_path):
    janela = MainWindow(
        Config(api_key="k", provider="gemini", vision_model="gemini-x", camera_source="x.jpg",
               history_dir=tmp_path),
        lambda f, p: Assistant(frame_provider=f, recorder=FakeRecorder(), stt=FakeSTT(),
                               vision=FakeVision(), speaker=FakeSpeaker()),
        start_camera=False)
    janela.show()
    yield janela
    janela.close()


def botoes_de_pagina(w):
    return w.nav._grupo.buttons()


def test_comeca_no_assistente_com_as_paginas_na_barra(w):
    assert w.stack.currentIndex() == w.paginas["assistente"] == 0
    assert {"assistente", "ajuda"} <= set(w.paginas)
    assert [b.text() for b in botoes_de_pagina(w)][:1] == ["Assistente"]
    assert botoes_de_pagina(w)[0].isChecked()


def test_clicar_na_barra_troca_de_pagina(w, app):
    w.nav._grupo.button(w.paginas["ajuda"]).click()
    assert w.stack.currentWidget() is w.help_page
    assert w.nav.current() == w.paginas["ajuda"]
    w.nav._grupo.button(w.paginas["assistente"]).click()
    assert w.stack.currentIndex() == w.paginas["assistente"]


def test_ir_para_sincroniza_a_barra_e_ignora_indice_invalido(w):
    w._ir_para(w.paginas["ajuda"])
    assert w.nav.current() == w.paginas["ajuda"]
    w._ir_para(99)
    assert w.stack.currentIndex() == w.paginas["ajuda"]


def test_f11_entra_e_sai_da_tela_cheia(w, app):
    w._alternar_tela_cheia()
    assert esperar(app, w.isFullScreen)
    assert w.nav.fullscreen_button.isChecked() and w.nav.fullscreen_button.text() == "Sair"
    w._alternar_tela_cheia()
    assert esperar(app, lambda: not w.isFullScreen())
    assert not w.nav.fullscreen_button.isChecked()


def test_esc_sai_da_tela_cheia_quando_nao_esta_gravando(w, app):
    w._alternar_tela_cheia()
    assert esperar(app, w.isFullScreen)
    w._on_escape()
    assert esperar(app, lambda: not w.isFullScreen())


def test_botao_de_tela_cheia_da_barra(w, app):
    w.nav.fullscreen_button.click()
    assert esperar(app, w.isFullScreen)
    w.nav.fullscreen_button.click()
    assert esperar(app, lambda: not w.isFullScreen())


def test_ajuda_mostra_atalhos_e_o_provedor_configurado(w):
    textos = " ".join(l.text() for l in w.help_page.findChildren(QLabel))
    for tecla, _ in ATALHOS:
        assert tecla in textos
    assert "F11" in textos and "Gemini" in textos and "gemini-x" in textos
    assert str(w.config.history_dir) in textos
