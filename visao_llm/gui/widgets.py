"""Componentes visuais reutilizáveis."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)


def scrollable(label: QLabel) -> QScrollArea:
    """Coloca um QLabel com quebra de linha em uma área rolável.

    Textos longos (como respostas da IA) deixam de ser cortados: a barra de rolagem vertical
    aparece só quando o texto não cabe, e a horizontal nunca (o texto quebra a linha).
    """
    area = QScrollArea()
    area.setObjectName("textScroll")
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    area.setWidget(label)
    label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    return area


class ImageView(QLabel):
    """QLabel que mantém a proporção da imagem ao redimensionar."""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._pix: QPixmap | None = None
        self._placeholder = placeholder
        self.setObjectName("imageView")
        self.setWordWrap(True)  # o aviso de "sem imagem" quebra a linha em colunas estreitas
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.clear_image()

    def set_image(self, img: QImage) -> None:
        self._pix = QPixmap.fromImage(img)
        self.setText("")
        self._rescale()

    def clear_image(self, texto: str | None = None) -> None:
        self._pix = None
        self.setPixmap(QPixmap())
        self.setText(texto if texto is not None else self._placeholder)

    def has_image(self) -> bool:
        return self._pix is not None

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._pix is not None and not self._pix.isNull():
            self.setPixmap(self._pix.scaled(self.size(), Qt.KeepAspectRatio,
                                            Qt.SmoothTransformation))

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(480, 360)


class Card(QFrame):
    """Cartão com título e conteúdo."""

    def __init__(self, titulo: str, conteudo: QWidget | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 16)
        self._layout.setSpacing(10)
        topo = QHBoxLayout()
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("cardTitle")
        topo.addWidget(self.titulo)
        topo.addStretch(1)
        self.acoes = topo
        self._layout.addLayout(topo)
        if conteudo is not None:
            self._layout.addWidget(conteudo, 1)

    def add(self, w: QWidget, stretch: int = 0) -> None:
        self._layout.addWidget(w, stretch)


class StepIndicator(QWidget):
    """Mostra em qual etapa do fluxo a aplicação está (RF05)."""

    ETAPAS = [
        ("OUVINDO", "1  Ouvir"),
        ("CAPTURANDO", "2  Capturar"),
        ("TRANSCREVENDO", "3  Transcrever"),
        ("PROCESSANDO", "4  Analisar"),
        ("FALANDO", "5  Falar"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._labels: dict[str, QLabel] = {}
        for i, (chave, texto) in enumerate(self.ETAPAS):
            lbl = QLabel(texto)
            lbl.setObjectName("step")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setProperty("estado", "pendente")
            self._labels[chave] = lbl
            lay.addWidget(lbl, 1)
            if i < len(self.ETAPAS) - 1:
                seta = QLabel("›")
                seta.setObjectName("stepArrow")
                lay.addWidget(seta)
        self._ordem = [c for c, _ in self.ETAPAS]

    def set_state(self, estado: str, origem: str = "voz") -> None:
        pular = {"OUVINDO", "TRANSCREVENDO"} if origem == "texto" else set()
        if estado in ("OCIOSO",):
            for c, lbl in self._labels.items():
                self._apply(lbl, "pendente")
            return
        if estado == "CONCLUIDO":
            for c, lbl in self._labels.items():
                self._apply(lbl, "pulado" if c in pular else "feito")
            return
        if estado == "ERRO":
            for c, lbl in self._labels.items():
                if lbl.property("estado") == "ativo":
                    self._apply(lbl, "erro")
            return
        if estado not in self._ordem:
            return
        idx = self._ordem.index(estado)
        for i, c in enumerate(self._ordem):
            if c in pular:
                self._apply(self._labels[c], "pulado")
            elif i < idx:
                self._apply(self._labels[c], "feito")
            elif i == idx:
                self._apply(self._labels[c], "ativo")
            else:
                self._apply(self._labels[c], "pendente")

    @staticmethod
    def _apply(lbl: QLabel, estado: str) -> None:
        lbl.setProperty("estado", estado)
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
