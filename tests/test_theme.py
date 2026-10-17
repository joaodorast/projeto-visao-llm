"""Tema cinza e branco com detalhes em laranja: paleta centralizada e sem cores fixas no código."""

import re
from pathlib import Path

import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui import style  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.pipeline import Assistant  # noqa: E402

GUI = Path(style.__file__).parent


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(style.STYLE)
    return a


def test_destaque_e_laranja_e_o_azul_antigo_saiu():
    assert style.ACCENT.lower() == "#f97316"
    assert style.ACCENT in style.STYLE
    for azul in ("#2563eb", "#1d4ed8", "#0f2747", "#eef2f8"):
        assert azul not in style.STYLE.lower()


def test_cores_da_janela_vem_da_folha_de_estilo():
    """Nenhuma cor fixa em main_window/sidebar/widgets: tudo passa pelo style.py."""
    for nome in ("main_window.py", "sidebar.py", "widgets.py"):
        codigo = (GUI / nome).read_text(encoding="utf-8")
        assert not re.search(r"#[0-9a-fA-F]{6}", codigo), f"cor fixa em {nome}"


def test_indicador_da_camera_usa_propriedade_de_estado(app, tmp_path):
    w = MainWindow(Config(api_key="k", camera_source="x.jpg", history_dir=tmp_path),
                   lambda f, p: Assistant(frame_provider=f, recorder=FakeRecorder(), stt=FakeSTT(),
                                          vision=FakeVision(), speaker=FakeSpeaker()),
                   start_camera=False)
    try:
        w._on_camera_status(True, "ok")
        assert w.cam_badge.property("estado") == "ok" and "ao vivo" in w.cam_badge.text()
        w._on_camera_status(False, "Câmera indisponível")
        assert w.cam_badge.property("estado") == "falha" and "sem sinal" in w.cam_badge.text()
    finally:
        w.close()
