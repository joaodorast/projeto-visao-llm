"""Textos longos rolam em vez de ficar cortados; a janela não passa do tamanho da tela."""

import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel, QScrollArea  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402
from visao_llm.gui.widgets import scrollable  # noqa: E402
from visao_llm.pipeline import Assistant  # noqa: E402

LONGO = " ".join(f"Frase {i} da resposta longa, com bastante detalhe sobre a cena." for i in range(40))


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


def area_do(label):
    pai = label.parent()
    while pai is not None and not isinstance(pai, QScrollArea):
        pai = pai.parent()
    return pai


def janela(tmp_path):
    cfg = Config(api_key="k", camera_source="nenhuma.jpg", history_dir=tmp_path)
    return MainWindow(cfg, lambda frames, player: Assistant(
        frame_provider=frames, recorder=FakeRecorder(), stt=FakeSTT(), vision=FakeVision(),
        speaker=FakeSpeaker()), start_camera=False)


def test_texto_longo_gera_barra_de_rolagem_vertical(app):
    label = QLabel(LONGO)
    label.setWordWrap(True)
    area = scrollable(label)
    area.resize(300, 150)
    area.show()
    app.processEvents()
    assert area.verticalScrollBar().maximum() > 0
    assert area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert area.horizontalScrollBar().maximum() == 0  # o texto quebra a linha
    area.close()


def test_texto_curto_nao_precisa_rolar(app):
    label = QLabel("Vejo um notebook.")
    label.setWordWrap(True)
    area = scrollable(label)
    area.resize(300, 150)
    area.show()
    app.processEvents()
    assert area.verticalScrollBar().maximum() == 0
    area.close()


def test_resposta_longa_na_janela_pode_ser_lida_ate_o_fim(app, tmp_path):
    w = janela(tmp_path)
    try:
        w.resize(1180, 700)
        w.show()
        w._set_text(w.answer_label, LONGO, "")
        app.processEvents()
        barra = area_do(w.answer_label).verticalScrollBar()
        assert barra.maximum() > 0
        barra.setValue(barra.maximum())
        assert barra.value() == barra.maximum()
        assert w.answer_label.text() == LONGO  # o texto não é truncado, só rolado
    finally:
        w.close()


def test_pergunta_longa_tambem_rola(app, tmp_path):
    w = janela(tmp_path)
    try:
        w.resize(1180, 700)
        w.show()
        w._set_text(w.question_label, LONGO, "")
        app.processEvents()
        assert area_do(w.question_label).verticalScrollBar().maximum() > 0
    finally:
        w.close()


def test_janela_inicial_cabe_na_area_util_da_tela(app, tmp_path):
    util = QApplication.primaryScreen().availableGeometry()
    w = janela(tmp_path)
    try:
        assert w.width() <= util.width() and w.height() <= util.height()
        assert w.minimumWidth() <= util.width() and w.minimumHeight() <= util.height()
    finally:
        w.close()
