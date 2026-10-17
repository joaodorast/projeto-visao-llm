"""Página de Diagnóstico: chave, câmera, microfone, alto-falante e conexão, dentro do app.

As verificações rodam em uma QThread (a de conexão pode levar alguns segundos) e cada item é
atualizado assim que termina.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from ..config import Config
from ..diagnostics import CheckResult, checks, run_check

DICAS = {
    "Chave da API": "Defina a chave do provedor no .env (GEMINI_API_KEY ou OPENAI_API_KEY) e "
                    "reinicie o app.",
    "Câmera": "Feche outros apps que usam a webcam (Teams, Zoom, navegador) ou troque a câmera "
              "em CAMERA no .env.",
    "Microfone": "Conecte um microfone e confira o dispositivo de entrada padrão do sistema. "
                 "Enquanto isso, dá para digitar as perguntas.",
    "Alto-falante": "Confira a saída de áudio padrão do sistema. A resposta continua aparecendo "
                    "na tela.",
}
DICA_CONEXAO = ("Verifique a internet, a chave e os nomes dos modelos no .env. Se a mensagem "
                "falar em limite de uso, aguarde ou confira os créditos da conta.")


class DiagnosticsWorker(QThread):
    started_check = pyqtSignal(int)
    finished_check = pyqtSignal(int, object)  # índice, CheckResult

    def __init__(self, itens: list[tuple[str, Callable[[], str]]], parent=None):
        super().__init__(parent)
        self.itens = itens

    def run(self) -> None:
        for i, (nome, verificacao) in enumerate(self.itens):
            self.started_check.emit(i)
            self.finished_check.emit(i, run_check(nome, verificacao))


class CheckRow(QFrame):
    """Uma linha da lista: selo de estado, nome, detalhe e dica em caso de falha."""

    SELOS = {"pendente": "—", "rodando": "…", "ok": "OK", "falha": "FALHA"}

    def __init__(self, nome: str, parent=None):
        super().__init__(parent)
        self.setObjectName("checkRow")
        self.nome = nome
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)
        self.badge = QLabel(objectName="checkBadge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedWidth(64)
        lay.addWidget(self.badge, 0, Qt.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(3)
        textos.addWidget(QLabel(nome, objectName="checkName"))
        self.detalhe = QLabel(objectName="checkDetail")
        self.detalhe.setWordWrap(True)
        self.detalhe.setTextInteractionFlags(Qt.TextSelectableByMouse)
        textos.addWidget(self.detalhe)
        self.dica = QLabel(objectName="checkHint")
        self.dica.setWordWrap(True)
        self.dica.hide()
        textos.addWidget(self.dica)
        lay.addLayout(textos, 1)
        self.set_estado("pendente", "Ainda não verificado.")

    @property
    def estado(self) -> str:
        return self.badge.property("estado")

    def set_estado(self, estado: str, detalhe: str = "", dica: str = "") -> None:
        self.badge.setText(self.SELOS[estado])
        self.badge.setProperty("estado", estado)
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.detalhe.setText(detalhe)
        self.dica.setText(dica)
        self.dica.setVisible(bool(dica))


class DiagnosticsPage(QScrollArea):
    def __init__(self, config: Config, camera_check: Callable[[], str] | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.config = config
        self.camera_check = camera_check
        self.worker: DiagnosticsWorker | None = None
        self.resultados: list[CheckResult | None] = []
        self.ja_executou = False

        corpo = QWidget(objectName="pageBody")
        self.setWidget(corpo)
        lay = QVBoxLayout(corpo)
        lay.setContentsMargins(32, 26, 32, 26)
        lay.setSpacing(16)

        topo = QHBoxLayout()
        titulos = QVBoxLayout()
        titulos.setSpacing(4)
        titulos.addWidget(QLabel("Diagnóstico", objectName="pageTitle"))
        sub = QLabel("Confere se chave, câmera, microfone, alto-falante e conexão estão prontos.",
                     objectName="pageSubtitle")
        sub.setWordWrap(True)
        titulos.addWidget(sub)
        topo.addLayout(titulos, 1)
        self.run_button = QPushButton("Executar diagnóstico", objectName="primary")
        self.run_button.setCursor(Qt.PointingHandCursor)
        self.run_button.clicked.connect(self.run)
        topo.addWidget(self.run_button, 0, Qt.AlignVCenter)
        lay.addLayout(topo)

        self.resumo = QLabel(objectName="diagSummary")
        self.resumo.setWordWrap(True)
        lay.addWidget(self.resumo)

        self.lista = QVBoxLayout()
        self.lista.setSpacing(10)
        lay.addLayout(self.lista)
        lay.addStretch(1)

        self.linhas: list[CheckRow] = []
        for nome, _ in checks(config, camera_check):
            linha = CheckRow(nome)
            self.linhas.append(linha)
            self.lista.addWidget(linha)
        self._set_resumo("neutro", "Clique em <b>Executar diagnóstico</b> para verificar o ambiente.")

    # ============================================================ execução
    @property
    def running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def run(self) -> None:
        if self.running:
            return
        self.ja_executou = True
        itens = checks(self.config, self.camera_check)
        self.resultados = [None] * len(itens)
        for linha in self.linhas:
            linha.set_estado("pendente", "Aguardando…")
        self.run_button.setEnabled(False)
        self.run_button.setText("Verificando…")
        self._set_resumo("rodando", "Verificando o ambiente…")
        self.worker = DiagnosticsWorker(itens, self)
        self.worker.started_check.connect(lambda i: self.linhas[i].set_estado("rodando", "Verificando…"))
        self.worker.finished_check.connect(self._on_result)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_result(self, i: int, r: CheckResult) -> None:
        self.resultados[i] = r
        dica = "" if r.ok else DICAS.get(r.nome, DICA_CONEXAO)
        self.linhas[i].set_estado("ok" if r.ok else "falha", r.detalhe, dica)

    def _on_finished(self) -> None:
        self.run_button.setEnabled(True)
        self.run_button.setText("Executar novamente")
        falhas = [r for r in self.resultados if r is not None and not r.ok]
        hora = datetime.now().strftime("%H:%M:%S")
        if falhas:
            n = len(falhas)
            self._set_resumo("falha", f"<b>{n} {'item precisa' if n == 1 else 'itens precisam'} "
                                      f"de atenção.</b> Veja as dicas abaixo. · verificado às {hora}")
        else:
            self._set_resumo("ok", f"<b>Tudo pronto!</b> O assistente pode ser usado. · "
                                   f"verificado às {hora}")

    def _set_resumo(self, estado: str, html: str) -> None:
        self.resumo.setText(html)
        self.resumo.setProperty("estado", estado)
        self.resumo.style().unpolish(self.resumo)
        self.resumo.style().polish(self.resumo)

    def wait(self, ms: int = 3000) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(ms)
