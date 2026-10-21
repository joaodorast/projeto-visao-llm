"""Câmera desligada no app: perguntas sem foto, do pipeline à interface."""

import json

import pytest

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision
from visao_llm.history import HistoryStore
from visao_llm.openai_service import VisionAssistant
from visao_llm.pipeline import Assistant, Callbacks


def test_pipeline_sem_frame_segue_sem_foto(tmp_path):
    capturadas = []
    vision = FakeVision()
    store = HistoryStore(tmp_path)
    a = Assistant(frame_provider=lambda: None, recorder=FakeRecorder(), stt=FakeSTT(),
                  vision=vision, speaker=FakeSpeaker(), store=store)

    r = a.ask_by_text("Quanto é 12 vezes 8?", Callbacks(on_captured=capturadas.append))

    assert r.image_jpeg == b"" and r.frame is None
    assert vision.chamadas[-1][0] == b""      # o modelo recebe a pergunta sem imagem
    assert capturadas == []                   # nada de foto na interface
    entrada, = store.load()
    assert entrada.imagem is None and entrada.pergunta == "Quanto é 12 vezes 8?"
    registro = json.loads((tmp_path / "interacoes.jsonl").read_text(encoding="utf-8"))
    assert registro["imagem"] is None
    assert not list(tmp_path.rglob("*.jpg"))


def test_mensagem_sem_foto_avisa_o_modelo():
    va = VisionAssistant(client=None, model="m")
    msgs = va.build_messages(b"", "O que você vê?")
    ultima = msgs[-1]
    assert ultima["role"] == "user" and isinstance(ultima["content"], str)
    assert ultima["content"].startswith("O que você vê?")
    assert "câmera está desligada" in ultima["content"]
    assert "câmera desligada" in msgs[0]["content"]  # instrução no prompt de sistema


def test_mensagem_com_foto_continua_igual():
    va = VisionAssistant(client=None, model="m")
    ultima = va.build_messages(b"\xff\xd8jpeg", "O que você vê?")[-1]
    assert [p["type"] for p in ultima["content"]] == ["text", "image_url"]


# ------------------------------------------------------------- interface
PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication  # noqa: E402

from test_gui import esperar  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


@pytest.fixture
def janela(app, tmp_path, imagem_teste):
    vision = FakeVision()
    w = MainWindow(Config(api_key="k", camera_source=str(imagem_teste), history_dir=tmp_path),
                   lambda f, p: Assistant(frame_provider=f, recorder=FakeRecorder(), stt=FakeSTT(),
                                          vision=vision, speaker=FakeSpeaker(),
                                          store=HistoryStore(tmp_path)))
    w.vision_fake = vision
    w.show()
    yield w
    w.close()


def test_desligar_e_ligar_a_camera(app, janela):
    w = janela
    assert esperar(app, w.live_view.has_image)
    w.camera_button.click()
    assert not w._camera_ligada and not w.camera_thread.isRunning()
    assert w.cam_badge.property("estado") == "off" and "desligada" in w.cam_badge.text()
    assert w.camera_button.text() == "Ligar câmera"
    for _ in range(20):  # quadros que ainda estavam na fila não podem voltar a aparecer
        app.processEvents()
    assert not w.live_view.has_image() and "Câmera desligada" in w.live_view.text()
    assert w._frame_atual() is None
    assert "desligada" in w._checar_camera()

    w.camera_button.click()
    assert w._camera_ligada and w.camera_button.text() == "Desligar câmera"
    assert esperar(app, w.live_view.has_image)
    assert w._frame_atual() is not None


def test_pergunta_com_a_camera_desligada(app, janela):
    w = janela
    assert esperar(app, w.live_view.has_image)
    w._alternar_camera()
    w._start("Quanto é 12 vezes 8?")
    assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO")
    assert w.vision_fake.chamadas[-1][0] == b""
    assert not w.captured_view.has_image()
    assert "câmera está desligada" in w.captured_view.text()
    assert w.answer_label.text() == "Vejo um notebook e uma garrafa sobre a mesa."
    assert not w.error_banner.isVisible()


def test_ligar_de_novo_o_assistente_usa_a_nova_captura(app, janela):
    w = janela
    assert esperar(app, w.live_view.has_image)
    w._get_assistant()
    w._alternar_camera()
    w._alternar_camera()
    assert esperar(app, w.live_view.has_image)
    w._start("O que está na mesa?")
    assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO")
    assert w.vision_fake.chamadas[-1][0] != b""  # voltou a mandar foto
    assert w.captured_view.has_image()
