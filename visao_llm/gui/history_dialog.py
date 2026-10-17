"""Tela de histórico: todas as conversas salvas em disco, com busca e miniaturas.

Esquerda: lista agrupada por dia (Hoje, Ontem, data) com miniatura da foto e a pergunta.
Direita: foto usada, pergunta, resposta completa e tempos da interação selecionada.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from PyQt5.QtCore import QSize, Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from ..history import HistoryEntry, HistoryStore
from .widgets import Card, ImageView

LIMITE_LISTA = 500  # evita carregar milhares de miniaturas de uma vez
NOMES_TEMPO = {"gravacao": "gravação", "captura": "captura", "stt": "transcrição",
               "llm": "análise", "tts": "voz"}


def rotulo_dia(dia: date, hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    if dia == hoje:
        return "Hoje"
    if dia == hoje - timedelta(days=1):
        return "Ontem"
    return dia.strftime("%d/%m/%Y")


def resumo(texto: str, limite: int = 70) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[:limite - 1].rstrip() + "…"


class HistoryDialog(QDialog):
    def __init__(self, store: HistoryStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = store
        self._entradas: list[HistoryEntry] = []
        self.setWindowTitle("Histórico de conversas")
        self.resize(1080, 680)
        self.setMinimumSize(820, 520)
        self.setObjectName("historyDialog")
        self._build_ui()
        self.reload()

    # ================================================================ UI
    def _build_ui(self) -> None:
        principal = QHBoxLayout(self)
        principal.setContentsMargins(18, 18, 18, 18)
        principal.setSpacing(16)

        # --- lista (esquerda)
        esquerda = QVBoxLayout()
        esquerda.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar nas perguntas e respostas…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._populate)
        esquerda.addWidget(self.search)

        self.list = QListWidget(objectName="historyList")
        self.list.setIconSize(QSize(72, 54))
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setMinimumWidth(330)
        self.list.currentItemChanged.connect(self._on_selected)
        lista_card = Card("Conversas", self.list)
        self.count_label = QLabel(objectName="hint")
        lista_card.acoes.addWidget(self.count_label)
        esquerda.addWidget(lista_card, 1)
        principal.addLayout(esquerda, 4)  # largura mínima vem da lista (330 px)

        # --- detalhe (direita)
        direita = QVBoxLayout()
        direita.setSpacing(12)
        self.image_view = ImageView("Selecione uma conversa")
        direita.addWidget(Card("Imagem capturada", self.image_view), 4)

        self.meta_label = QLabel(objectName="hint")
        self.question_label = QLabel(objectName="questionText")
        self.question_label.setWordWrap(True)
        self.question_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.question_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        pergunta_card = Card("Pergunta", self.question_label)
        pergunta_card.acoes.addWidget(self.meta_label)
        direita.addWidget(pergunta_card, 0)

        self.answer_label = QLabel(objectName="answerText")
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.answer_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        direita.addWidget(Card("Resposta da IA", self.answer_label), 3)

        rodape = QHBoxLayout()
        self.folder_button = QPushButton("📂  Abrir pasta dos registros", objectName="secondary")
        self.folder_button.setCursor(Qt.PointingHandCursor)
        self.folder_button.clicked.connect(self._open_folder)
        self.refresh_button = QPushButton("↻  Atualizar", objectName="secondary")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(self.reload)
        close = QPushButton("Fechar", objectName="secondary")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.close)
        rodape.addWidget(self.folder_button)
        rodape.addWidget(self.refresh_button)
        rodape.addStretch(1)
        rodape.addWidget(close)
        direita.addLayout(rodape)
        principal.addLayout(direita, 6)

        self._mostrar(None)

    # ============================================================= dados
    def reload(self) -> None:
        self._entradas = self.store.load(LIMITE_LISTA)
        self._populate()

    def _filtradas(self) -> list[HistoryEntry]:
        termo = self.search.text().strip().lower()
        if not termo:
            return self._entradas
        return [e for e in self._entradas
                if termo in e.pergunta.lower() or termo in e.resposta.lower()]

    def _populate(self) -> None:
        atual = self._selecionada()
        self.list.blockSignals(True)
        self.list.clear()
        visiveis = self._filtradas()
        dia_atual: date | None = None
        escolher: QListWidgetItem | None = None
        for entrada in visiveis:
            dia = entrada.data_hora.date()
            if dia != dia_atual:
                dia_atual = dia
                cab = QListWidgetItem(rotulo_dia(dia).upper())
                cab.setFlags(Qt.NoItemFlags)
                fonte = cab.font()
                fonte.setBold(True)
                fonte.setPointSizeF(max(7.0, fonte.pointSizeF() - 2))
                cab.setFont(fonte)
                cab.setData(Qt.UserRole + 1, "cabecalho")
                self.list.addItem(cab)
            item = QListWidgetItem(self._texto_item(entrada))
            item.setData(Qt.UserRole, entrada)
            item.setToolTip(entrada.resposta)
            if entrada.imagem is not None:
                pix = QPixmap(str(entrada.imagem))
                if not pix.isNull():
                    item.setIcon(QIcon(pix.scaled(72, 54, Qt.KeepAspectRatio,
                                                  Qt.SmoothTransformation)))
            self.list.addItem(item)
            if atual is not None and entrada is atual:
                escolher = item
        self.list.blockSignals(False)

        total, mostrados = len(self._entradas), len(visiveis)
        self.count_label.setText(f"{mostrados} de {total}" if self.search.text().strip()
                                 else f"{total}")
        if escolher is None:
            escolher = next((self.list.item(i) for i in range(self.list.count())
                             if self.list.item(i).data(Qt.UserRole) is not None), None)
        if escolher is not None:
            self.list.setCurrentItem(escolher)
        else:
            self._mostrar(None)

    @staticmethod
    def _texto_item(e: HistoryEntry) -> str:
        icone = "🎤" if e.origem == "voz" else "⌨"
        return f"{e.data_hora:%H:%M}  {icone}  {resumo(e.pergunta)}\n{resumo(e.resposta, 80)}"

    def _selecionada(self) -> HistoryEntry | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    # ========================================================== detalhe
    def _on_selected(self, item: QListWidgetItem | None, _anterior=None) -> None:
        self._mostrar(item.data(Qt.UserRole) if item is not None else None)

    def _mostrar(self, e: HistoryEntry | None) -> None:
        if e is None:
            vazio = "Nenhuma conversa salva ainda." if not self._entradas \
                else "Nenhum resultado para a busca."
            self.image_view.clear_image("Selecione uma conversa")
            self._set_text(self.question_label, None, vazio)
            self._set_text(self.answer_label, None, "A resposta aparecerá aqui.")
            self.meta_label.setText("")
            return
        if e.imagem is not None:
            img = QImage(str(e.imagem))
            if not img.isNull():
                self.image_view.set_image(img)
            else:
                self.image_view.clear_image("Imagem ilegível")
        else:
            self.image_view.clear_image("Imagem não encontrada no disco")
        self._set_text(self.question_label, e.pergunta, "")
        self._set_text(self.answer_label, e.resposta, "")
        tempos = ", ".join(f"{NOMES_TEMPO.get(k, k)} {v:.1f}s" for k, v in e.tempos.items())
        self.meta_label.setText(f"{e.data_hora:%d/%m/%Y %H:%M:%S}  ·  "
                                f"{'voz' if e.origem == 'voz' else 'texto'}"
                                + (f"  ·  {tempos}" if tempos else ""))

    @staticmethod
    def _set_text(label: QLabel, texto: str | None, vazio: str) -> None:
        label.setText(texto if texto else vazio)
        label.setProperty("vazio", "false" if texto else "true")
        label.style().unpolish(label)
        label.style().polish(label)

    # ============================================================ ações
    def _open_folder(self) -> None:
        pasta = Path(self.store.pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(pasta))  # noqa: S606 - abre o Explorer na pasta
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))
