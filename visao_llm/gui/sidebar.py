"""Barra lateral de conversas (estilo chat de IA): nova conversa, busca, lista e exclusão.

Só emite sinais; quem carrega, apaga e confirma é a janela principal.
"""

from __future__ import annotations

from datetime import date, timedelta

from PyQt5.QtCore import QSize, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                             QPushButton, QVBoxLayout, QWidget)

from ..history import Conversation
from .icons import plus_icon, search_icon, trash_icon

QUADROS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # animação de carregamento (um quadro a cada 55 ms)
INTERVALO_MS = 55
QUADROS_TOTAIS = 11  # ~0,6 s no total
PARADO = "↻"

ROLE_ID = Qt.UserRole
ROLE_SALVA = Qt.UserRole + 1  # False para a conversa atual que ainda não tem nada gravado


def rotulo_dia(dia: date, hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    if dia == hoje:
        return "Hoje"
    if dia == hoje - timedelta(days=1):
        return "Ontem"
    return dia.strftime("%d/%m/%Y")


def plural(n: int) -> str:
    return f"{n} pergunta" if n == 1 else f"{n} perguntas"


class ConversationSidebar(QFrame):
    new_requested = pyqtSignal()
    conversation_selected = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    LARGURA = 288

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(self.LARGURA)
        self._conversas: list[Conversation] = []
        self._atual = ""
        self._gravando = True

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 16, 14, 14)
        lay.setSpacing(10)

        titulo = QHBoxLayout()
        titulo.addWidget(QLabel("Conversas", objectName="sidebarTitle"))
        titulo.addStretch(1)
        self.refresh_button = QPushButton(PARADO, objectName="refreshChats")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setToolTip("Atualizar a lista com o que está salvo em disco")
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        titulo.addWidget(self.refresh_button)
        lay.addLayout(titulo)
        self._spinner = QTimer(self)
        self._spinner.setInterval(INTERVALO_MS)
        self._spinner.timeout.connect(self._girar)
        self._quadro = 0
        self.new_button = QPushButton("  Nova conversa", objectName="newChat")
        self.new_button.setIcon(plus_icon())
        self.new_button.setIconSize(QSize(18, 18))
        self.new_button.setCursor(Qt.PointingHandCursor)
        self.new_button.setToolTip("Começa uma conversa nova; as anteriores continuam salvas (Ctrl+N)")
        self.new_button.clicked.connect(self.new_requested)
        lay.addWidget(self.new_button)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar conversas…")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(search_icon(), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self._populate)
        lay.addWidget(self.search)

        self.list = QListWidget(objectName="conversationList")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setWordWrap(True)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._menu)
        self.list.itemClicked.connect(self._on_clicked)
        lay.addWidget(self.list, 1)

        self.hint = QLabel(objectName="hint")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        self.delete_button = QPushButton("  Apagar conversa", objectName="danger")
        self.delete_button.setIcon(trash_icon())
        self.delete_button.setIconSize(QSize(18, 18))
        self.delete_button.setToolTip("Apaga a conversa selecionada e as fotos dela (pede confirmação)")
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        lay.addWidget(self.delete_button)
        self._atualizar_rodape()

    # ============================================================= dados
    def refresh(self, conversas: list[Conversation], atual: str, gravando: bool = True) -> None:
        self._conversas = conversas
        self._atual = atual
        self._gravando = gravando
        self._populate()

    def _populate(self) -> None:
        termo = self.search.text().strip().lower()
        self.list.blockSignals(True)
        self.list.clear()

        salvas = {c.id for c in self._conversas}
        if self._atual and self._atual not in salvas and not termo:
            novo = QListWidgetItem("Nova conversa\nfaça uma pergunta para começar")
            novo.setData(ROLE_ID, self._atual)
            novo.setData(ROLE_SALVA, False)
            self.list.addItem(novo)

        dia_atual: date | None = None
        for conversa in self._conversas:
            if termo and not any(termo in e.pergunta.lower() or termo in e.resposta.lower()
                                 for e in conversa.entradas):
                continue
            dia = conversa.atualizada.date()
            if dia != dia_atual:
                dia_atual = dia
                cab = QListWidgetItem(rotulo_dia(dia).upper())
                cab.setFlags(Qt.NoItemFlags)
                fonte = cab.font()
                fonte.setBold(True)
                fonte.setPointSizeF(max(7.0, fonte.pointSizeF() - 2))
                cab.setFont(fonte)
                self.list.addItem(cab)
            item = QListWidgetItem(
                f"{conversa.titulo}\n{plural(len(conversa.entradas))}  ·  "
                f"{conversa.atualizada:%H:%M}")
            item.setData(ROLE_ID, conversa.id)
            item.setData(ROLE_SALVA, True)
            item.setToolTip(conversa.entradas[0].pergunta)
            self.list.addItem(item)

        for i in range(self.list.count()):
            if self.list.item(i).data(ROLE_ID) == self._atual:
                self.list.setCurrentRow(i)
                break
        self.list.blockSignals(False)
        self._atualizar_rodape()

    def _atualizar_rodape(self) -> None:
        item = self.list.currentItem()
        self.delete_button.setEnabled(item is not None and bool(item.data(ROLE_SALVA)))
        if not self._gravando:
            self.hint.setText("A gravação do histórico está desativada (SALVAR_HISTORICO=false): "
                              "as conversas não serão salvas.")
        elif not self._conversas:
            self.hint.setText("Suas conversas ficam salvas automaticamente e aparecem aqui.")
        else:
            self.hint.setText("")

    # ============================================================ ações
    def _on_refresh_clicked(self) -> None:
        """Pede a releitura do disco agora e mostra uma animação curta de carregamento."""
        if self._spinner.isActive():
            return
        self.refresh_requested.emit()
        self._quadro = 0
        self.refresh_button.setEnabled(False)
        self._girar()
        self._spinner.start()

    def _girar(self) -> None:
        if self._quadro >= QUADROS_TOTAIS:
            self._spinner.stop()
            self.refresh_button.setText(PARADO)
            self.refresh_button.setEnabled(True)
            return
        self.refresh_button.setText(QUADROS[self._quadro % len(QUADROS)])
        self._quadro += 1

    def _on_clicked(self, item: QListWidgetItem) -> None:
        sid = item.data(ROLE_ID)
        if sid:
            self.conversation_selected.emit(sid)
        self._atualizar_rodape()

    def _on_delete_clicked(self) -> None:
        item = self.list.currentItem()
        if item is not None and item.data(ROLE_SALVA):
            self.delete_requested.emit(item.data(ROLE_ID))

    def _menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None or not item.data(ROLE_SALVA):
            return
        menu = QMenu(self)
        menu.addAction("Abrir", lambda: self.conversation_selected.emit(item.data(ROLE_ID)))
        menu.addAction("Apagar conversa", lambda: self.delete_requested.emit(item.data(ROLE_ID)))
        menu.exec_(self.list.viewport().mapToGlobal(pos))
