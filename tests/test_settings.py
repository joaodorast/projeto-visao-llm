"""Página Ajustes: carregar, trocar provedor, salvar no .env e aplicar na hora."""

from dataclasses import replace

import pytest
from dotenv import dotenv_values

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from visao_llm.config import PADROES_PROVEDOR, Config  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.gui.settings_page import SettingsPage  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402
from visao_llm.gui.widgets import Toggle  # noqa: E402
from visao_llm.pipeline import Assistant  # noqa: E402

ENV = "PROVEDOR=gemini\nGEMINI_API_KEY=chave-gemini\nOPENAI_API_KEY=\n#MODELO_VISAO=\nCAMERA=0\n"


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    for var in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    env = tmp_path / ".env"
    env.write_text(ENV, encoding="utf-8")
    g = PADROES_PROVEDOR["gemini"]
    return Config(provider="gemini", api_key="chave-gemini", base_url=g["base_url"],
                  vision_model=g["vision_model"], stt_model=g["stt_model"], tts_model=g["tts_model"],
                  tts_voice=g["tts_voice"], camera_source=0, env_path=env,
                  history_dir=tmp_path / "reg")


class Aplicador:
    def __init__(self, aceita=True):
        self.aceita, self.recebidos = aceita, []

    def __call__(self, novo):
        self.recebidos.append(novo)
        return self.aceita


def test_carrega_a_configuracao_sem_mostrar_a_chave(app, cfg):
    page = SettingsPage(cfg, Aplicador())
    assert page.provedor == "gemini"
    assert page.vision_model.text() == cfg.vision_model
    assert page.camera.text() == "0"
    assert page.api_key.text() == "" and "configurada" in page.api_key.placeholderText()
    assert page.tts_enabled.isChecked() and page.save_history.isChecked()


def test_trocar_provedor_troca_os_modelos_padrao_e_avisa_sem_chave(app, cfg):
    page = SettingsPage(cfg, Aplicador())
    page.provider.setCurrentIndex(page.provider.findData("openai"))
    o = PADROES_PROVEDOR["openai"]
    assert page.vision_model.text() == o["vision_model"]
    assert page.tts_voice.text() == o["tts_voice"]
    assert "Nenhuma chave" in page.key_hint.text()


def test_modelo_personalizado_nao_e_sobrescrito_ao_trocar_provedor(app, cfg):
    page = SettingsPage(cfg, Aplicador())
    page.vision_model.setText("meu-modelo")
    page.provider.setCurrentIndex(page.provider.findData("openai"))
    assert page.vision_model.text() == "meu-modelo"
    page.defaults_button.click()
    assert page.vision_model.text() == PADROES_PROVEDOR["openai"]["vision_model"]


def test_salvar_grava_no_env_e_aplica(app, cfg):
    aplicar = Aplicador()
    page = SettingsPage(cfg, aplicar)
    page.camera.setText("1")
    page.silence.setValue(2.0)
    page.tts_enabled.setChecked(False)
    page.save_button.click()

    novo = aplicar.recebidos[-1]
    assert novo.camera_source == 1 and novo.silence_seconds == 2.0 and novo.tts_enabled is False
    assert novo.api_key == "chave-gemini"  # campo vazio mantém a chave
    valores = dotenv_values(cfg.env_path)
    assert valores["CAMERA"] == "1" and valores["SILENCIO_SEG"] == "2"
    assert valores["TTS_ATIVO"] == "false"
    assert valores["GEMINI_API_KEY"] == "chave-gemini"
    assert valores["MODELO_VISAO"] == ""  # no padrão: fica vazio para não fixar o modelo
    assert "salvos e aplicados" in page.status.text()


def test_salvar_nova_chave_e_provedor(app, cfg):
    aplicar = Aplicador()
    page = SettingsPage(cfg, aplicar)
    page.provider.setCurrentIndex(page.provider.findData("openai"))
    page.api_key.setText("sk-nova")
    page.save_button.click()

    novo = aplicar.recebidos[-1]
    assert novo.provider == "openai" and novo.api_key == "sk-nova" and novo.base_url is None
    valores = dotenv_values(cfg.env_path)
    assert valores["PROVEDOR"] == "openai" and valores["OPENAI_API_KEY"] == "sk-nova"
    assert valores["GEMINI_API_KEY"] == "chave-gemini"  # a do outro provedor fica
    assert page.api_key.text() == ""  # a chave não fica exposta no campo


def test_voltar_ao_provedor_anterior_recupera_a_chave(app, cfg):
    aplicar = Aplicador()
    page = SettingsPage(cfg, aplicar)
    page.provider.setCurrentIndex(page.provider.findData("openai"))
    page.api_key.setText("sk-nova")
    page.save_button.click()
    page.provider.setCurrentIndex(page.provider.findData("gemini"))
    page.save_button.click()
    assert aplicar.recebidos[-1].api_key == "chave-gemini"
    assert aplicar.recebidos[-1].base_url == PADROES_PROVEDOR["gemini"]["base_url"]


def test_nao_salva_se_o_app_estiver_ocupado(app, cfg):
    page = SettingsPage(cfg, Aplicador(aceita=False))
    page.camera.setText("3")
    page.save_button.click()
    assert dotenv_values(cfg.env_path)["CAMERA"] == "0"
    assert "Aguarde" in page.status.text()


def test_camera_vazia_e_recusada(app, cfg):
    aplicar = Aplicador()
    page = SettingsPage(cfg, aplicar)
    page.camera.setText("  ")
    page.save_button.click()
    assert aplicar.recebidos == [] and "câmera" in page.status.text().lower()


def test_descartar_volta_aos_valores_em_uso(app, cfg):
    page = SettingsPage(cfg, Aplicador())
    page.camera.setText("9")
    page.api_key.setText("xyz")
    page.discard_button.click()
    assert page.camera.text() == "0" and page.api_key.text() == ""


def test_toggle_liga_e_desliga_com_clique(app):
    t = Toggle("Opção")
    t.resize(t.sizeHint())
    t.show()
    assert not t.isChecked()
    t.click()
    assert t.isChecked()
    assert t.sizeHint().width() > Toggle.TRILHO_L
    t.close()


# -------------------------------------------------------------- janela
@pytest.fixture
def janela(app, cfg):
    w = MainWindow(cfg, lambda f, p: Assistant(frame_provider=f, recorder=FakeRecorder(),
                                               stt=FakeSTT(), vision=FakeVision(),
                                               speaker=FakeSpeaker()),
                   start_camera=False)
    yield w
    w.close()


def test_janela_tem_a_pagina_ajustes_na_ordem(janela):
    assert list(janela.paginas) == ["assistente", "diagnostico", "ajustes", "ajuda"]


def test_aplicar_troca_provedor_sem_reiniciar(janela, cfg):
    janela._get_assistant()
    assert janela._assistant is not None
    novo = replace(cfg, provider="openai", vision_model="gpt-4.1-mini", api_key="sk-x",
                   base_url=None)

    assert janela._aplicar_config(novo) is True

    assert janela.config is novo
    assert janela._assistant is None  # recriado na próxima pergunta
    assert "OpenAI" in janela.subtitle.text() and "gpt-4.1-mini" in janela.subtitle.text()
    assert janela.diagnostics_page.linhas[-1].nome == "Conexão com OpenAI"
    assert "gpt-4.1-mini" in janela.help_page.sobre_label.text()


def test_aplicar_nova_camera_reinicia_a_captura(janela, cfg):
    antiga = janela.camera_thread
    janela._aplicar_config(replace(cfg, camera_source=2))
    assert janela.camera_thread is not antiga
    assert janela.config.camera_source == 2


def test_aplicar_e_recusado_durante_uma_pergunta(janela, cfg, monkeypatch):
    monkeypatch.setattr(type(janela), "busy", property(lambda self: True))
    assert janela._aplicar_config(replace(cfg, camera_source=5)) is False
    assert janela.config.camera_source == 0


def test_interruptor_de_conversa_continua_e_salvo(app, cfg):
    aplicar = Aplicador()
    page = SettingsPage(cfg, aplicar)
    assert page.continuous.isChecked()
    page.continuous.setChecked(False)
    page.save_button.click()
    assert aplicar.recebidos[-1].continuous_conversation is False
    assert dotenv_values(cfg.env_path)["CONVERSA_CONTINUA"] == "false"


def test_aplicar_conversa_continua_troca_o_texto_do_botao(janela, cfg):
    from visao_llm.gui.main_window import TEXTO_CONVERSA, TEXTO_MIC
    assert janela.mic_button.text() == TEXTO_CONVERSA
    janela._aplicar_config(replace(cfg, continuous_conversation=False))
    assert janela.mic_button.text() == TEXTO_MIC
