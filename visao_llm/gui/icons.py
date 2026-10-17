"""Ícones vetoriais desenhados com QPainter (nítidos em qualquer escala, sem arquivos de imagem).

Cada ícone devolve um QIcon com três estados, para o botão reagir ao mouse:
normal, ativo (mouse por cima) e desativado.
"""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

TAMANHO = 20  # lado do ícone, em pixels lógicos
ESCALA = 3    # desenhado em 3x para ficar nítido em telas de alta densidade


def _desenhar(forma: Callable[[QPainter], None], cor: str) -> QPixmap:
    pix = QPixmap(TAMANHO * ESCALA, TAMANHO * ESCALA)
    pix.setDevicePixelRatio(ESCALA)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    caneta = QPen(QColor(cor), 1.7)
    caneta.setCapStyle(Qt.RoundCap)
    caneta.setJoinStyle(Qt.RoundJoin)
    p.setPen(caneta)
    p.setBrush(Qt.NoBrush)
    forma(p)
    p.end()
    return pix


def _icone(forma: Callable[[QPainter], None], normal: str, ativo: str, desativado: str) -> QIcon:
    icone = QIcon()
    icone.addPixmap(_desenhar(forma, normal), QIcon.Normal)
    icone.addPixmap(_desenhar(forma, ativo), QIcon.Active)
    icone.addPixmap(_desenhar(forma, desativado), QIcon.Disabled)
    return icone


def _lixeira(p: QPainter) -> None:
    # tampa e alça
    p.drawLine(QPointF(4, 6), QPointF(16, 6))
    alca = QPainterPath()
    alca.moveTo(8, 6)
    alca.lineTo(8, 4.2)
    alca.quadTo(8, 3.4, 8.8, 3.4)
    alca.lineTo(11.2, 3.4)
    alca.quadTo(12, 3.4, 12, 4.2)
    alca.lineTo(12, 6)
    p.drawPath(alca)
    # corpo
    corpo = QPainterPath()
    corpo.moveTo(5.4, 6)
    corpo.lineTo(6.1, 15.2)
    corpo.quadTo(6.2, 16.6, 7.6, 16.6)
    corpo.lineTo(12.4, 16.6)
    corpo.quadTo(13.8, 16.6, 13.9, 15.2)
    corpo.lineTo(14.6, 6)
    p.drawPath(corpo)
    # frisos
    p.drawLine(QPointF(8.4, 9), QPointF(8.7, 14))
    p.drawLine(QPointF(11.6, 9), QPointF(11.3, 14))


def _mais(p: QPainter) -> None:
    p.drawLine(QPointF(10, 4.5), QPointF(10, 15.5))
    p.drawLine(QPointF(4.5, 10), QPointF(15.5, 10))


def _lupa(p: QPainter) -> None:
    p.drawEllipse(QRectF(3.8, 3.8, 9, 9))
    p.drawLine(QPointF(12.4, 12.4), QPointF(16.2, 16.2))


def trash_icon() -> QIcon:
    """Lixeira: rosa claro normal, branca ao passar o mouse, cinza azulado se desativada."""
    return _icone(_lixeira, "#fca5a5", "#ffffff", "#5b7396")


def plus_icon() -> QIcon:
    return _icone(_mais, "#ffffff", "#ffffff", "#9db4d8")


def search_icon() -> QIcon:
    return _icone(_lupa, "#7f9cc6", "#ffffff", "#5b7396")
