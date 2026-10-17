"""Barra de navegação (trilho de ícones à esquerda): troca de página e tela cheia.

Só emite sinais; a janela principal decide qual página mostrar.
"""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QButtonGroup, QFrame, QLabel, QToolButton, QVBoxLayout, QWidget

from .icons import fullscreen_icon


class NavRail(QFrame):
    page_requested = pyqtSignal(int)
    fullscreen_requested = pyqtSignal()

    LARGURA = 78

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("navRail")
        self.setFixedWidth(self.LARGURA)
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._grupo.idClicked.connect(self.page_requested)

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(8, 14, 8, 12)
        self._lay.setSpacing(6)
        marca = QLabel("VI", objectName="appMark")
        marca.setAlignment(Qt.AlignCenter)
        marca.setFixedSize(38, 38)
        marca.setToolTip("Visão e Interpretação do Ambiente")
        self._lay.addWidget(marca, 0, Qt.AlignHCenter)
        self._lay.addSpacing(14)
        self._fim_paginas = self._lay.count()
        self._lay.addStretch(1)

        self.fullscreen_button = self._botao("Tela cheia", fullscreen_icon())
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.setToolTip("Tela cheia (F11)")
        self.fullscreen_button.clicked.connect(self.fullscreen_requested)
        self._lay.addWidget(self.fullscreen_button)

    def _botao(self, texto: str, icone: QIcon) -> QToolButton:
        botao = QToolButton(objectName="navButton")
        botao.setText(texto)
        botao.setIcon(icone)
        botao.setIconSize(QSize(22, 22))
        botao.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        botao.setCursor(Qt.PointingHandCursor)
        botao.setFixedWidth(self.LARGURA - 16)
        return botao

    def add_page(self, texto: str, icone: Callable[[], QIcon], atalho: str = "") -> int:
        """Adiciona um botão de página e devolve o índice dela."""
        indice = len(self._grupo.buttons())
        botao = self._botao(texto, icone())
        botao.setCheckable(True)
        botao.setToolTip(f"{texto} ({atalho})" if atalho else texto)
        self._grupo.addButton(botao, indice)
        self._lay.insertWidget(self._fim_paginas + indice, botao)
        if indice == 0:
            botao.setChecked(True)
        return indice

    def set_current(self, indice: int) -> None:
        botao = self._grupo.button(indice)
        if botao is not None:
            botao.setChecked(True)

    def current(self) -> int:
        return self._grupo.checkedId()

    def set_fullscreen(self, ativo: bool) -> None:
        self.fullscreen_button.setChecked(ativo)
        self.fullscreen_button.setText("Sair" if ativo else "Tela cheia")
        self.fullscreen_button.setToolTip("Sair da tela cheia (F11 ou Esc)" if ativo
                                          else "Tela cheia (F11)")
