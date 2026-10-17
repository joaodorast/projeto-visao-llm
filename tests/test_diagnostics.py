"""Diagnóstico: coleta dos resultados (terminal) e página dentro do app."""

import pytest

from visao_llm import diagnostics
from visao_llm.config import Config
from visao_llm.diagnostics import CheckResult, collect_diagnostics, run_check, run_diagnostics
from visao_llm.errors import CameraError, ConfigError


def test_run_check_converte_erros_em_falha():
    assert run_check("x", lambda: "tudo certo") == CheckResult("x", True, "tudo certo")
    def falha():
        raise CameraError("Câmera indisponível.")
    assert run_check("Câmera", falha) == CheckResult("Câmera", False, "Câmera indisponível.")


def test_coleta_na_ordem_e_usa_a_camera_fornecida(monkeypatch):
    monkeypatch.setattr(diagnostics, "_alto_falante", lambda: "Alto-falantes")
    monkeypatch.setattr(diagnostics, "_api", lambda cfg: "conectado")
    monkeypatch.setattr(diagnostics.AudioRecorder, "check_available", lambda self: "Microfone USB")
    cfg = Config(api_key="k", provider="gemini")

    resultados = collect_diagnostics(cfg, camera_check=lambda: "câmera do app")

    assert [r.nome for r in resultados] == ["Chave da API", "Câmera", "Microfone", "Alto-falante",
                                            "Conexão com Gemini"]
    assert all(r.ok for r in resultados)
    assert resultados[1].detalhe == "câmera do app"


def test_sem_chave_aparece_como_falha_sem_quebrar(monkeypatch):
    monkeypatch.setattr(diagnostics, "_alto_falante", lambda: "ok")
    monkeypatch.setattr(diagnostics.AudioRecorder, "check_available", lambda self: "ok")
    def sem_chave(cfg):
        raise ConfigError("Chave da Gemini não configurada.")
    monkeypatch.setattr(diagnostics, "_api", sem_chave)
    resultados = collect_diagnostics(Config(api_key=None, provider="gemini"), camera_check=lambda: "ok")
    assert not resultados[0].ok and "GEMINI_API_KEY" in resultados[0].detalhe
    assert not resultados[-1].ok


def test_saida_do_terminal_mantem_o_formato(monkeypatch, capsys):
    monkeypatch.setattr(diagnostics, "collect_diagnostics", lambda cfg: [
        CheckResult("Chave da API", True, "ok"), CheckResult("Câmera", False, "sem câmera"),
        CheckResult("Conexão com Gemini", True, "conectado")])
    assert run_diagnostics(Config()) is False
    saida = capsys.readouterr().out
    assert "[OK   ] Chave da API (RNF01)" in saida
    assert "[FALHA] Câmera (RF01)" in saida
    assert "Conexão com Gemini (RF03)" in saida
    assert "Corrija os itens com FALHA" in saida


# ------------------------------------------------------------------ página
PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication  # noqa: E402

from test_gui import esperar  # noqa: E402
from visao_llm.gui.diagnostics_page import DiagnosticsPage  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


@pytest.fixture
def ambiente(monkeypatch):
    monkeypatch.setattr(diagnostics, "_alto_falante", lambda: "Alto-falantes")
    monkeypatch.setattr(diagnostics.AudioRecorder, "check_available", lambda self: "Microfone USB")
    monkeypatch.setattr(diagnostics, "_api", lambda cfg: "conectado")


def test_pagina_mostra_todos_ok(app, ambiente):
    page = DiagnosticsPage(Config(api_key="k", provider="gemini"), camera_check=lambda: "640x480")
    assert [l.estado for l in page.linhas] == ["pendente"] * 5
    page.run()
    assert esperar(app, lambda: page.run_button.isEnabled(), 5)
    assert [l.estado for l in page.linhas] == ["ok"] * 5
    assert "Tudo pronto" in page.resumo.text()
    assert page.run_button.isEnabled() and page.run_button.text() == "Executar novamente"


def test_pagina_mostra_falha_com_dica(app, ambiente):
    def sem_camera():
        raise CameraError("Câmera indisponível no momento.")
    page = DiagnosticsPage(Config(api_key="k", provider="gemini"), camera_check=sem_camera)
    page.run()
    assert esperar(app, lambda: page.run_button.isEnabled(), 5)
    camera = page.linhas[1]
    assert camera.estado == "falha" and "indisponível" in camera.detalhe.text()
    assert camera.dica.isVisibleTo(page) and "webcam" in camera.dica.text()
    assert "1 item precisa de atenção" in page.resumo.text()


def test_janela_roda_o_diagnostico_na_primeira_visita(app, ambiente, tmp_path):
    from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision
    from visao_llm.gui.main_window import MainWindow
    from visao_llm.pipeline import Assistant
    w = MainWindow(Config(api_key="k", camera_source="x.jpg", history_dir=tmp_path),
                   lambda f, p: Assistant(frame_provider=f, recorder=FakeRecorder(), stt=FakeSTT(),
                                          vision=FakeVision(), speaker=FakeSpeaker()),
                   start_camera=False)
    try:
        assert not w.diagnostics_page.ja_executou
        w._ir_para(w.paginas["diagnostico"])
        assert w.diagnostics_page.ja_executou
        # sem a câmera do app ligada, o item da câmera falha sem derrubar nada
        assert esperar(app, lambda: w.diagnostics_page.linhas[1].estado == "falha", 5)
        assert esperar(app, lambda: w.diagnostics_page.run_button.isEnabled(), 5)
    finally:
        w.close()
