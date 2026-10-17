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


def _icone(forma: Callable[[QPainter], None], normal: str, ativo: str, desativado: str,
           marcado: str | None = None) -> QIcon:
    """`marcado` é a cor quando o botão está selecionado (botões checáveis, como a navegação)."""
    icone = QIcon()
    icone.addPixmap(_desenhar(forma, normal), QIcon.Normal)
    icone.addPixmap(_desenhar(forma, ativo), QIcon.Active)
    icone.addPixmap(_desenhar(forma, desativado), QIcon.Disabled)
    if marcado is not None:
        selecionado = _desenhar(forma, marcado)
        icone.addPixmap(selecionado, QIcon.Normal, QIcon.On)
        icone.addPixmap(selecionado, QIcon.Active, QIcon.On)
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
    """Lixeira: rosa claro normal, branca ao passar o mouse, cinza se desativada."""
    return _icone(_lixeira, "#fca5a5", "#ffffff", "#63636b")


def plus_icon() -> QIcon:
    return _icone(_mais, "#f97316", "#ea580c", "#a1a1aa")  # laranja sobre o botão branco


def search_icon() -> QIcon:
    return _icone(_lupa, "#a1a1aa", "#f4f4f5", "#63636b")


# --- navegação ----------------------------------------------------------------
def _balao(p: QPainter) -> None:
    balao = QPainterPath()
    balao.addRoundedRect(QRectF(3, 3.5, 14, 10.5), 3, 3)
    p.drawPath(balao)
    p.drawLine(QPointF(7, 14), QPointF(6, 17))
    p.drawLine(QPointF(6, 17), QPointF(10, 14))
    p.drawLine(QPointF(6.8, 7.6), QPointF(13.2, 7.6))
    p.drawLine(QPointF(6.8, 10.2), QPointF(11, 10.2))


def _pulso(p: QPainter) -> None:
    linha = QPainterPath()
    linha.moveTo(2.5, 10.5)
    for x, y in ((6, 10.5), (8, 5), (11.5, 15.5), (13.5, 10.5), (17.5, 10.5)):
        linha.lineTo(x, y)
    p.drawPath(linha)


def _engrenagem(p: QPainter) -> None:
    import math
    centro = QPointF(10, 10)
    p.drawEllipse(centro, 2.6, 2.6)
    p.drawEllipse(centro, 5.6, 5.6)
    for i in range(8):
        ang = math.radians(i * 45)
        p.drawLine(QPointF(10 + 5.6 * math.cos(ang), 10 + 5.6 * math.sin(ang)),
                   QPointF(10 + 7.8 * math.cos(ang), 10 + 7.8 * math.sin(ang)))


def _ajuda(p: QPainter) -> None:
    p.drawEllipse(QPointF(10, 10), 7.5, 7.5)
    interrogacao = QPainterPath()
    interrogacao.moveTo(7.6, 8)
    interrogacao.cubicTo(7.6, 5, 12.4, 5, 12.4, 8)
    interrogacao.cubicTo(12.4, 9.6, 10, 9.8, 10, 11.6)
    p.drawPath(interrogacao)
    p.drawPoint(QPointF(10, 14.2))


def _tela_cheia(p: QPainter) -> None:
    for (x, y, dx, dy) in ((3.5, 3.5, 1, 1), (16.5, 3.5, -1, 1), (3.5, 16.5, 1, -1), (16.5, 16.5, -1, -1)):
        p.drawLine(QPointF(x, y), QPointF(x + 4 * dx, y))
        p.drawLine(QPointF(x, y), QPointF(x, y + 4 * dy))


_CORES_NAV = dict(normal="#8b8b94", ativo="#f4f4f5", desativado="#52525b", marcado="#f97316")


def chat_icon() -> QIcon:
    return _icone(_balao, **_CORES_NAV)


def pulse_icon() -> QIcon:
    return _icone(_pulso, **_CORES_NAV)


def gear_icon() -> QIcon:
    return _icone(_engrenagem, **_CORES_NAV)


def help_icon() -> QIcon:
    return _icone(_ajuda, **_CORES_NAV)


def fullscreen_icon() -> QIcon:
    return _icone(_tela_cheia, **_CORES_NAV)
