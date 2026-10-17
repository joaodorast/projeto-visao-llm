"""Inicialização da aplicação Qt."""

from __future__ import annotations

import logging
import sys
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from ..config import Config
from ..factory import build_assistant
from .main_window import MainWindow
from .style import STYLE

log = logging.getLogger(__name__)


def _install_excepthook() -> None:
    """Qualquer exceção não prevista é registrada e mostrada — o app não fecha (RNF02)."""

    def hook(tipo, valor, tb):
        log.error("Exceção não tratada:\n%s", "".join(traceback.format_exception(tipo, valor, tb)))
        app = QApplication.instance()
        if app is not None:
            QMessageBox.warning(None, "Erro inesperado",
                                f"Ocorreu um erro inesperado, mas o aplicativo continua aberto.\n\n"
                                f"{tipo.__name__}: {valor}\n\nDetalhes em logs/app.log.")

    sys.excepthook = hook


def run_gui(config: Config) -> int:
    if QApplication.instance() is None:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Visão LLM")
    app.setStyleSheet(STYLE)
    _install_excepthook()

    janela = MainWindow(config, lambda frames, player: build_assistant(config, frames, player))
    app.aboutToQuit.connect(janela.shutdown)
    janela.show()
    if not config.api_key:
        janela._show_error("Configuração", "OPENAI_API_KEY não definida. Copie .env.example "
                                           "para .env, coloque sua chave e reinicie o app.")
    return app.exec_()
