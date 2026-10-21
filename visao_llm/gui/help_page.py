"""Página de Ajuda: como usar, atalhos, conversas e informações do app."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from .. import __version__
from ..config import Config, nome_provedor
from .widgets import Card

ATALHOS = [
    ("Ctrl + Espaço", "Começa a conversa por voz; de novo, encerra"),
    ("Esc", "Corta a resposta falada; ouvindo, encerra a conversa; sai da tela cheia"),
    ("Enter", "Envia a pergunta digitada"),
    ("Ctrl + N", "Nova conversa"),
    ("Ctrl + 1, 2, …", "Vai para as páginas da barra de navegação, na ordem"),
    ("F11", "Entra e sai da tela cheia"),
    ("Ctrl + Shift + C", "Liga e desliga a câmera (desligada, as perguntas vão sem foto)"),
]

PASSOS = [
    ("Comece a conversa", "Clique em <b>Começar conversa</b> (ou <b>Ctrl+Espaço</b>) uma vez. "
                          "A partir daí é só falar: o app percebe quando você começa e termina "
                          "cada pergunta. Também dá para digitar."),
    ("A IA olha", "No instante em que você termina de falar, a câmera tira a foto que vai junto com a "
                  "pergunta."),
    ("Ela responde", "A resposta aparece na tela e é falada. Use <b>Repetir</b> para ouvir de novo."),
    ("Continue ou encerre", "Depois de responder, o app volta a ouvir sozinho, com o contexto das "
                            "últimas trocas. Para terminar, diga <b>“encerrar conversa”</b> (ou "
                            "“pode parar”, “tchau”) ou clique em <b>Encerrar conversa</b>. "
                            "<b>Nova conversa</b> começa do zero."),
]


def _texto(html: str, nome: str = "helpText") -> QLabel:
    label = QLabel(html, objectName=nome)
    label.setWordWrap(True)
    label.setTextFormat(Qt.RichText)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


class HelpPage(QScrollArea):
    def __init__(self, config: Config, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        conteudo = QWidget(objectName="pageBody")
        self.setWidget(conteudo)
        lay = QVBoxLayout(conteudo)
        lay.setContentsMargins(32, 26, 32, 26)
        lay.setSpacing(16)

        lay.addWidget(QLabel("Ajuda", objectName="pageTitle"))
        lay.addWidget(_texto("Tudo o que você precisa para usar o assistente.", "pageSubtitle"))

        # --- como usar
        como = Card("Como usar")
        grade = QGridLayout()
        grade.setHorizontalSpacing(14)
        grade.setVerticalSpacing(12)
        for i, (titulo, texto) in enumerate(PASSOS):
            numero = QLabel(str(i + 1), objectName="stepNumber")
            numero.setAlignment(Qt.AlignCenter)
            numero.setFixedSize(28, 28)
            grade.addWidget(numero, i, 0, Qt.AlignTop)
            grade.addWidget(_texto(f"<b>{titulo}</b><br>{texto}"), i, 1)
        grade.setColumnStretch(1, 1)
        como._layout.addLayout(grade)
        lay.addWidget(como)

        # --- atalhos
        atalhos = Card("Atalhos de teclado")
        tabela = QGridLayout()
        tabela.setHorizontalSpacing(18)
        tabela.setVerticalSpacing(10)
        for i, (tecla, acao) in enumerate(ATALHOS):
            kbd = QLabel(tecla, objectName="kbd")
            kbd.setAlignment(Qt.AlignCenter)
            tabela.addWidget(kbd, i, 0)
            tabela.addWidget(_texto(acao), i, 1)
        tabela.setColumnStretch(1, 1)
        atalhos._layout.addLayout(tabela)
        lay.addWidget(atalhos)

        # --- conversas e dados
        dados = Card("Conversas e dados")
        dados.add(_texto(
            "Cada pergunta é salva automaticamente na conversa atual e aparece na barra "
            "<b>Conversas</b>. Clique em uma conversa para reabri-la e continuar; use a lixeira "
            "para apagar (pede confirmação)."
            f"<br><br>Os registros ficam em <code>{config.history_dir}</code> "
            "(<code>interacoes.jsonl</code> e as fotos por dia). Para não gravar nada, defina "
            "<code>SALVAR_HISTORICO=false</code> (ou desligue em <b>Ajustes</b>)."
            "<br><br>Provedor, chave, modelos, câmera e voz podem ser trocados na página "
            "<b>Ajustes</b>, sem reiniciar o app."))
        lay.addWidget(dados)

        # --- sobre
        sobre = Card("Sobre")
        self.sobre_label = _texto("")
        sobre.add(self.sobre_label)
        lay.addWidget(sobre)
        self.set_config(config)
        lay.addStretch(1)

    def set_config(self, config: Config) -> None:
        self.sobre_label.setText(
            f"<b>Visão e Interpretação do Ambiente</b> · versão {__version__}<br>"
            f"Provedor: <b>{nome_provedor(config.provider)}</b> · visão <code>{config.vision_model}</code> · "
            f"transcrição <code>{config.stt_model}</code> · voz <code>{config.tts_model}</code><br>"
            "Documentação na pasta <code>docs/</code> do projeto.")
