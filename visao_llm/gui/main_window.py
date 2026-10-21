"""Janela principal (RF05): câmera ao vivo, imagem capturada, pergunta e resposta."""

from __future__ import annotations

import logging
from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QKeySequence
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QProgressBar, QPushButton, QShortcut,
                             QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from ..audio import AudioPlayer
from ..config import Config, nome_provedor
from ..errors import AppError
from ..history import HistoryStore
from ..models import InteractionResult, State, new_session_id
from ..openai_service import Turn
from ..pipeline import Assistant, FrameProvider
from .diagnostics_page import DiagnosticsPage
from .help_page import HelpPage
from .icons import chat_icon, gear_icon, help_icon, pulse_icon
from .navigation import NavRail
from .settings_page import SettingsPage
from .sidebar import ConversationSidebar
from .widgets import Card, ImageView, StepIndicator, scrollable
from .workers import (CameraThread, ConversationWorker, InteractionWorker, SpeakWorker,
                      frame_to_qimage)

log = logging.getLogger(__name__)

AssistantFactory = Callable[[FrameProvider, AudioPlayer], Assistant]

TIPO_PILL = {
    "OCIOSO": "ocioso", "OUVINDO": "ouvindo", "CAPTURANDO": "trabalhando",
    "TRANSCREVENDO": "trabalhando", "PROCESSANDO": "trabalhando", "FALANDO": "falando",
    "CONCLUIDO": "ok", "ERRO": "erro",
}

TEXTO_MIC = "🎤  Clique para falar"
TEXTO_CONVERSA = "🎤  Começar conversa"
TEXTO_ENCERRAR = "■  Encerrar conversa"
DICA_CONVERSA = ("Conversa ativa: fale quando quiser, sem clicar de novo  ·  diga "
                 "\u201cencerrar conversa\u201d ou clique em Encerrar para terminar")


class MainWindow(QMainWindow):
    def __init__(self, config: Config, assistant_factory: AssistantFactory,
                 start_camera: bool = True):
        super().__init__()
        self.config = config
        self.assistant_factory = assistant_factory
        self.player = AudioPlayer()
        self._assistant: Assistant | None = None
        self._worker: InteractionWorker | None = None
        self._speak_worker: SpeakWorker | None = None
        self._estado = "OCIOSO"
        self._origem = "voz"
        self._resultados: list[InteractionResult] = []
        self._ultima_resposta: str | None = None
        self._conversa_id = new_session_id()
        self._camera_ligada = True
        self._conversa_ativa = False
        self._history_store = HistoryStore(config.history_dir)

        self.setWindowTitle("Visão e Interpretação do Ambiente com LLM")
        self._ajustar_tamanho()
        self._build_ui()
        self._set_state("OCIOSO")
        self._refresh_sidebar()

        self.camera_thread = CameraThread(config.camera_source, parent=self)
        self.camera_thread.frame_ready.connect(self._on_frame)
        self.camera_thread.status_changed.connect(self._on_camera_status)
        if start_camera:
            self.camera_thread.start()

    def _ajustar_tamanho(self) -> None:
        """Tamanho inicial que cabe na tela (a janela não passa da área útil, sem a barra de tarefas)."""
        tela = QApplication.primaryScreen()
        util = tela.availableGeometry() if tela is not None else None
        largura = min(1440, util.width()) if util else 1440
        altura = min(820, util.height()) if util else 820
        self.resize(largura, altura)
        self.setMinimumSize(min(1180, largura), min(640, altura))

    # ================================================================ UI
    def _build_ui(self) -> None:
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        raiz = QHBoxLayout(root)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # --- navegação: trilho de ícones + páginas empilhadas
        self.nav = NavRail()
        self.nav.page_requested.connect(self._ir_para)
        self.nav.fullscreen_requested.connect(self._alternar_tela_cheia)
        raiz.addWidget(self.nav)
        self.stack = QStackedWidget()
        raiz.addWidget(self.stack, 1)
        self.paginas: dict[str, int] = {}

        assistente = QWidget()
        pagina = QHBoxLayout(assistente)  # a página do assistente: conversas + conteúdo
        pagina.setContentsMargins(0, 0, 0, 0)
        pagina.setSpacing(0)
        self._adicionar_pagina("assistente", "Assistente", chat_icon, assistente)
        self.sidebar = ConversationSidebar()
        self.sidebar.new_requested.connect(self._on_clear)
        self.sidebar.conversation_selected.connect(self._abrir_conversa)
        self.sidebar.delete_requested.connect(self._on_delete_conversation)
        self.sidebar.refresh_requested.connect(self._atualizar_do_disco)
        pagina.addWidget(self.sidebar)
        conteudo = QWidget()
        pagina.addWidget(conteudo, 1)
        principal = QVBoxLayout(conteudo)
        principal.setContentsMargins(22, 18, 22, 14)
        principal.setSpacing(14)

        # --- cabeçalho
        topo = QHBoxLayout()
        titulos = QVBoxLayout()
        titulos.setSpacing(2)
        titulos.addWidget(QLabel("Visão e Interpretação do Ambiente", objectName="appTitle"))
        self.subtitle = QLabel(objectName="appSubtitle")
        titulos.addWidget(self.subtitle)
        topo.addLayout(titulos, 1)
        self.status_pill = QLabel(objectName="statusPill")
        topo.addWidget(self.status_pill, 0, Qt.AlignVCenter)
        principal.addLayout(topo)

        self.steps = StepIndicator()
        principal.addWidget(self.steps)

        # --- banners
        self.error_banner = QLabel(objectName="errorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        principal.addWidget(self.error_banner)
        self.warn_banner = QLabel(objectName="warnBanner")
        self.warn_banner.setWordWrap(True)
        self.warn_banner.hide()
        principal.addWidget(self.warn_banner)

        corpo = QHBoxLayout()
        corpo.setSpacing(16)
        principal.addLayout(corpo, 1)

        # --- coluna esquerda: câmera + controles
        esquerda = QVBoxLayout()
        esquerda.setSpacing(12)
        self.live_view = ImageView("Conectando à câmera…")
        self.live_card = Card("Câmera ao vivo", self.live_view)
        self.cam_badge = QLabel("● conectando", objectName="camBadge")
        self.live_card.acoes.addWidget(self.cam_badge)
        self.camera_button = QPushButton("Desligar câmera", objectName="secondary")
        self.camera_button.setCursor(Qt.PointingHandCursor)
        self.camera_button.setToolTip("Liga e desliga a câmera (Ctrl+Shift+C). "
                                      "Desligada, as perguntas vão sem foto.")
        self.camera_button.clicked.connect(self._alternar_camera)
        self.live_card.acoes.addWidget(self.camera_button)
        esquerda.addWidget(self.live_card, 1)

        controles = Card("Pergunta")
        self.mic_button = QPushButton(self._texto_mic(), objectName="micButton")
        self.mic_button.setCursor(Qt.PointingHandCursor)
        self.mic_button.clicked.connect(self._on_mic_clicked)
        controles.add(self.mic_button)
        self.level_bar = QProgressBar(objectName="level")
        self.level_bar.setRange(0, 100)
        self.level_bar.setTextVisible(False)
        self.level_bar.setVisible(False)
        controles.add(self.level_bar)
        linha = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("…ou digite a pergunta e pressione Enter")
        self.text_input.returnPressed.connect(self._on_send_text)
        self.send_button = QPushButton("Enviar", objectName="secondary")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self._on_send_text)
        linha.addWidget(self.text_input, 1)
        linha.addWidget(self.send_button)
        controles._layout.addLayout(linha)
        self.conversation_hint = QLabel(DICA_CONVERSA, objectName="conversationHint")
        self.conversation_hint.setWordWrap(True)
        self.conversation_hint.hide()
        controles.add(self.conversation_hint)
        controles.add(QLabel("Atalhos: Ctrl+Espaço começa / encerra  ·  Esc interrompe a fala",
                             objectName="hint"))
        esquerda.addWidget(controles, 0)
        corpo.addLayout(esquerda, 4)

        # --- coluna direita: imagem capturada, pergunta, resposta, histórico
        direita = QVBoxLayout()
        direita.setSpacing(12)
        linha_topo = QHBoxLayout()
        linha_topo.setSpacing(12)
        self.captured_view = ImageView("A foto usada na pergunta aparece aqui")
        linha_topo.addWidget(Card("Imagem capturada", self.captured_view), 2)

        textos = QVBoxLayout()
        textos.setSpacing(12)
        self.question_label = QLabel(objectName="questionText")
        self.question_label.setWordWrap(True)
        self.question_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.question_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        pergunta_card = Card("Pergunta (texto)", scrollable(self.question_label))
        pergunta_card.setMaximumHeight(100)  # a resposta é que precisa de espaço
        textos.addWidget(pergunta_card, 1)

        self.answer_label = QLabel(objectName="answerText")
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.answer_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        resp_card = Card("Resposta da IA", scrollable(self.answer_label))
        self.repeat_button = QPushButton("🔊 Repetir", objectName="secondary")
        self.repeat_button.setCursor(Qt.PointingHandCursor)
        self.repeat_button.clicked.connect(self._on_repeat)
        self.repeat_button.setEnabled(False)
        resp_card.acoes.addWidget(self.repeat_button)
        textos.addWidget(resp_card, 6)
        linha_topo.addLayout(textos, 3)  # mais largura para o texto, que agora rola
        direita.addLayout(linha_topo, 7)

        self.history = QListWidget()
        self.history.itemClicked.connect(self._on_history_clicked)
        hist_card = Card("Perguntas desta conversa", self.history)
        self.clear_button = QPushButton("Nova conversa", objectName="secondary")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self._on_clear)
        hist_card.acoes.addWidget(self.clear_button)
        direita.addWidget(hist_card, 2)
        corpo.addLayout(direita, 6)

        self._set_text(self.question_label, None, "Nenhuma pergunta ainda.")
        self._set_text(self.answer_label, None, "A resposta da IA aparecerá aqui.")

        self._atualizar_textos_config()

        QShortcut(QKeySequence("Ctrl+Space"), self, activated=self._on_mic_clicked)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._on_clear)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self._on_escape)
        QShortcut(QKeySequence(Qt.Key_F11), self, activated=self._alternar_tela_cheia)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self._alternar_camera)

        self.diagnostics_page = DiagnosticsPage(self.config, camera_check=self._checar_camera)
        self._adicionar_pagina("diagnostico", "Diagnóstico", pulse_icon, self.diagnostics_page)
        self.settings_page = SettingsPage(self.config, on_apply=self._aplicar_config)
        self._adicionar_pagina("ajustes", "Ajustes", gear_icon, self.settings_page)
        self.help_page = HelpPage(self.config)
        self._adicionar_pagina("ajuda", "Ajuda", help_icon, self.help_page)
        for i in range(self.stack.count()):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self,
                      activated=lambda i=i: self._ir_para(i))

    @staticmethod
    def _set_text(label: QLabel, texto: str | None, vazio: str) -> None:
        label.setText(texto if texto else vazio)
        label.setProperty("vazio", "false" if texto else "true")
        label.style().unpolish(label)
        label.style().polish(label)

    # ============================================================ estados
    @property
    def busy(self) -> bool:
        return any(w is not None and w.isRunning() for w in (self._worker, self._speak_worker))

    def _set_state(self, nome: str, detalhe: str = "") -> None:
        self._estado = nome
        estado = State[nome]
        self.status_pill.setText(f"● {estado.value}")
        self.status_pill.setProperty("tipo", TIPO_PILL.get(nome, "ocioso"))
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.steps.set_state(nome, self._origem)

        modo, texto, ativo = "normal", self._texto_mic(), True
        if self._conversa_ativa:
            # durante a conversa o botão sempre encerra; a cor acompanha a etapa
            texto = TEXTO_ENCERRAR
            modo = {"OUVINDO": "ouvindo", "FALANDO": "falando"}.get(nome, "conversa")
        elif nome == "OUVINDO":
            modo, texto = "ouvindo", "■  Parar e enviar"
        elif nome in ("CAPTURANDO", "TRANSCREVENDO", "PROCESSANDO"):
            texto, ativo = "⏳  Processando…", False
        elif nome == "FALANDO":
            modo, texto = "falando", "■  Interromper fala"
        self.mic_button.setText(texto)
        self.mic_button.setEnabled(ativo)
        self.mic_button.setProperty("modo", modo)
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)
        self.level_bar.setVisible(nome == "OUVINDO")

        ocupado = nome in ("OUVINDO", "CAPTURANDO", "TRANSCREVENDO", "PROCESSANDO", "FALANDO")
        self.send_button.setEnabled(not ocupado)
        self.text_input.setEnabled(not ocupado)
        self.repeat_button.setEnabled(not ocupado and bool(self._ultima_resposta))

        if nome == "CONCLUIDO" and detalhe:
            self._show_warning(f"Resposta exibida, mas não falada: {detalhe}")

    def _show_error(self, titulo: str, mensagem: str) -> None:
        self.error_banner.setText(f"<b>{titulo}:</b> {mensagem}")
        self.error_banner.show()

    def _show_warning(self, mensagem: str) -> None:
        self.warn_banner.setText(mensagem)
        self.warn_banner.show()

    def _hide_banners(self) -> None:
        self.error_banner.hide()
        self.warn_banner.hide()

    # ============================================================ câmera
    def _on_frame(self, img: QImage) -> None:
        if not self._camera_ligada:  # quadro atrasado da captura que acabou de ser desligada
            return
        self.live_view.set_image(img)

    def _on_camera_status(self, ok: bool, msg: str) -> None:
        if not self._camera_ligada:  # sinal atrasado da captura que acabou de ser desligada
            return
        self.cam_badge.setText("● ao vivo" if ok else "● sem sinal")
        self.cam_badge.setProperty("estado", "ok" if ok else "falha")  # cor definida no style.py
        self.cam_badge.style().unpolish(self.cam_badge)
        self.cam_badge.style().polish(self.cam_badge)
        if not ok:
            self.live_view.clear_image(f"📷  {msg}\n\nTentando reconectar…")
        self.statusBar().showMessage(msg, 8000)

    # ============================================================ ações
    def _get_assistant(self) -> Assistant | None:
        if self._assistant is None:
            try:
                self._assistant = self.assistant_factory(self._frame_atual, self.player)
            except AppError as exc:
                self._show_error(exc.titulo, exc.mensagem)
                self._set_state("ERRO", exc.mensagem)
                return None
        return self._assistant

    def _texto_mic(self) -> str:
        return TEXTO_CONVERSA if self.config.continuous_conversation else TEXTO_MIC

    def _on_mic_clicked(self) -> None:
        if self._conversa_ativa:
            self._encerrar_conversa()
            return
        if self.config.continuous_conversation and not self.busy:
            self._iniciar_conversa()
            return
        if self._estado == "OUVINDO" and self._worker is not None:
            self._worker.stop_listening()
            return
        if self._estado == "FALANDO":
            self.player.stop()
            return
        if not self.busy:
            self._start(None)

    def _on_escape(self) -> None:
        if self._conversa_ativa:
            # na conversa, Esc corta a resposta falada; ouvindo, encerra a conversa
            if self._estado == "FALANDO":
                self.player.stop()
            else:
                self._encerrar_conversa()
            return
        if self._estado == "OUVINDO" and self._worker is not None:
            self._worker.stop_listening()
        elif self._estado == "FALANDO":
            self.player.stop()
        elif self.isFullScreen():
            self._alternar_tela_cheia()

    # ========================================================= navegação
    def _adicionar_pagina(self, chave: str, titulo: str, icone, widget: QWidget) -> int:
        indice = self.stack.addWidget(widget)
        self.nav.add_page(titulo, icone, f"Ctrl+{indice + 1}")
        self.paginas[chave] = indice
        return indice

    def _ir_para(self, indice: int) -> None:
        if 0 <= indice < self.stack.count():
            self.stack.setCurrentIndex(indice)
            self.nav.set_current(indice)
            # na primeira visita, o diagnóstico roda sozinho
            if self.stack.currentWidget() is self.diagnostics_page and not self.diagnostics_page.ja_executou:
                self.diagnostics_page.run()

    def _atualizar_textos_config(self) -> None:
        c = self.config
        self.subtitle.setText(f"Pergunte por voz — a IA olha pela câmera e responde falando  ·  "
                              f"{nome_provedor(c.provider)} · {c.vision_model}")
        self.statusBar().showMessage(
            f"Câmera: {c.camera_source}  ·  STT: {c.stt_model}  ·  "
            f"TTS: {c.tts_model if c.tts_enabled else 'desativado'}")

    def _aplicar_config(self, novo: Config) -> bool:
        """Aplica ajustes sem reiniciar. Devolve False se houver uma pergunta em andamento."""
        if self.busy:
            return False
        self.mic_button.setText(TEXTO_CONVERSA if novo.continuous_conversation else TEXTO_MIC)
        trocou_camera = novo.camera_source != self.config.camera_source
        self.config = novo
        self._assistant = None  # recriado na próxima pergunta, com o novo provedor/modelos
        self._history_store = HistoryStore(novo.history_dir)
        self._atualizar_textos_config()
        self.diagnostics_page.set_config(novo)
        self.help_page.set_config(novo)
        self._refresh_sidebar()
        if trocou_camera:
            self._reiniciar_camera()
        return True

    def _reiniciar_camera(self, forcar: bool = False) -> None:
        estava_ligada = forcar or (self._camera_ligada and self.camera_thread.isRunning())
        self.camera_thread.stop()
        self.camera_thread.wait(3000)
        self.camera_thread = CameraThread(self.config.camera_source, parent=self)
        self.camera_thread.frame_ready.connect(self._on_frame)
        self.camera_thread.status_changed.connect(self._on_camera_status)
        self.live_view.clear_image("Conectando à câmera…")
        if estava_ligada:
            self.camera_thread.start()

    def _frame_atual(self):
        """Frame para a pergunta: None com a câmera desligada (a pergunta vai sem foto)."""
        if not self._camera_ligada:
            return None
        return self.camera_thread.latest_frame()

    def _alternar_camera(self) -> None:
        """Liga ou desliga a câmera. Desligada, a captura para e as perguntas vão sem foto."""
        if self._camera_ligada:
            self._camera_ligada = False
            self.camera_thread.stop()
            self.camera_thread.wait(3000)
            self.live_view.clear_image("Câmera desligada\n\nAs perguntas vão sem foto.\n"
                                       "Clique em Ligar câmera para voltar.")
            self._badge("● desligada", "off")
            self.camera_button.setText("Ligar câmera")
            self.statusBar().showMessage("Câmera desligada: as perguntas vão sem foto.", 6000)
        else:
            self._camera_ligada = True
            self._reiniciar_camera(forcar=True)
            self._badge("● conectando", "")
            self.camera_button.setText("Desligar câmera")
        self.diagnostics_page.set_config(self.config)

    def _badge(self, texto: str, estado: str) -> None:
        self.cam_badge.setText(texto)
        self.cam_badge.setProperty("estado", estado)
        self.cam_badge.style().unpolish(self.cam_badge)
        self.cam_badge.style().polish(self.cam_badge)

    def _checar_camera(self) -> str:
        """Diagnóstico da câmera usando a que já está aberta (abrir de novo falharia no Windows)."""
        if not self._camera_ligada:
            return "desligada no app (as perguntas vão sem foto; use Ligar câmera)"
        frame = self.camera_thread.latest_frame()
        altura, largura = frame.shape[:2]
        return f"fonte={self.config.camera_source}, resolução={largura}x{altura} (em uso pelo app)"

    def _alternar_tela_cheia(self) -> None:
        """F11: entra e sai da tela cheia, voltando ao estado anterior (maximizada ou normal)."""
        if self.isFullScreen():
            if getattr(self, "_estava_maximizada", False):
                self.showMaximized()
            else:
                self.showNormal()
        else:
            self._estava_maximizada = self.isMaximized()
            self.showFullScreen()
        self.nav.set_fullscreen(self.isFullScreen())

    def _on_send_text(self) -> None:
        texto = self.text_input.text().strip()
        if not texto or self.busy:
            return
        self.text_input.clear()
        self._start(texto)

    def _start(self, pergunta_texto: str | None) -> None:
        self._hide_banners()
        assistant = self._get_assistant()
        if assistant is None:
            return
        self._sync_assistant(assistant)
        self._origem = "texto" if pergunta_texto is not None else "voz"
        w = InteractionWorker(assistant, pergunta_texto, speak=self.config.tts_enabled,
                              parent=self)
        w.state_changed.connect(self._set_state)
        w.level_changed.connect(lambda v: self.level_bar.setValue(min(100, int(v * 600))))
        w.image_captured.connect(self.captured_view.set_image)
        w.question_ready.connect(lambda q: self._set_text(self.question_label, q, ""))
        w.answer_ready.connect(self._on_answer)
        w.failed.connect(self._on_failed)
        w.finished.connect(self._on_worker_finished)
        self._worker = w
        if pergunta_texto is None:
            self._set_text(self.question_label, None, "Ouvindo sua pergunta…")
        self._set_text(self.answer_label, None, "Aguardando…")
        if not self._camera_ligada:
            self.captured_view.clear_image("Sem foto: a câmera está desligada")
        w.start()

    # ======================================================= modo conversa
    def _iniciar_conversa(self) -> None:
        """Um clique: o app ouve, responde e volta a ouvir até a conversa ser encerrada."""
        self._hide_banners()
        assistant = self._get_assistant()
        if assistant is None:
            return
        self._sync_assistant(assistant)
        self._origem = "voz"
        self._conversa_ativa = True
        w = ConversationWorker(assistant, speak=self.config.tts_enabled, player=self.player,
                               parent=self)
        w.state_changed.connect(self._set_state)
        w.level_changed.connect(lambda v: self.level_bar.setValue(min(100, int(v * 600))))
        w.image_captured.connect(self.captured_view.set_image)
        w.question_ready.connect(lambda q: self._set_text(self.question_label, q, ""))
        w.answer_ready.connect(self._on_answer)
        w.turn_done.connect(self._refresh_sidebar)
        w.turn_failed.connect(self._show_error)
        w.failed.connect(self._on_failed)
        w.ended.connect(self._on_conversa_encerrada)
        w.finished.connect(self._on_conversa_finished)
        self._worker = w
        self.conversation_hint.show()
        if not self._camera_ligada:
            self.captured_view.clear_image("Sem foto: a câmera está desligada")
        self._set_text(self.question_label, None, "Pode falar: estou ouvindo…")
        w.start()

    def _encerrar_conversa(self) -> None:
        if self._worker is not None and self._conversa_ativa:
            self._worker.stop_listening()
            self.mic_button.setEnabled(False)
            self.mic_button.setText("Encerrando…")

    def _on_conversa_encerrada(self, motivo: str) -> None:
        texto = ("Conversa encerrada a seu pedido." if motivo == "voz"
                 else "Conversa encerrada.")
        self.statusBar().showMessage(texto, 6000)

    def _on_conversa_finished(self) -> None:
        self._conversa_ativa = False
        self.conversation_hint.hide()
        if self._estado != "ERRO":
            self._set_state("OCIOSO")
        else:
            self._set_state("ERRO")
        self.mic_button.setEnabled(True)
        self.mic_button.setText(self._texto_mic())
        self._refresh_sidebar()

    def _on_answer(self, resultado: InteractionResult) -> None:
        self._ultima_resposta = resultado.resposta
        self._set_text(self.answer_label, resultado.resposta, "")
        self._resultados.append(resultado)
        self.history.insertItem(0, self._item_para(resultado, len(self._resultados) - 1))

    @staticmethod
    def _item_para(resultado: InteractionResult, indice: int) -> QListWidgetItem:
        hora = resultado.timestamp.strftime("%H:%M:%S")
        icone = "🎤" if resultado.origem == "voz" else "⌨"
        item = QListWidgetItem(f"{hora}  {icone}  {resultado.pergunta}")
        item.setData(Qt.UserRole, indice)
        item.setToolTip(resultado.resposta)
        return item

    def _on_failed(self, titulo: str, mensagem: str) -> None:
        self._show_error(titulo, mensagem)
        self._set_text(self.answer_label, None, "Sem resposta — veja o aviso acima.")
        if self._estado != "ERRO":
            self._set_state("ERRO", mensagem)

    def _on_worker_finished(self) -> None:
        if self._estado not in ("ERRO", "CONCLUIDO"):
            self._set_state("OCIOSO")
        else:
            self._set_state(self._estado)  # reabilita controles
            # mantém o estado visível, mas libera o botão
            self.mic_button.setEnabled(True)
            self.mic_button.setText(self._texto_mic())
        self._refresh_sidebar()  # a interação acabou de ser gravada em disco

    def _on_repeat(self) -> None:
        assistant = self._assistant
        if not self._ultima_resposta or assistant is None or assistant.speaker is None or self.busy:
            if assistant is not None and assistant.speaker is None:
                self._show_warning("A voz está desativada (TTS_ATIVO=false).")
            return
        self._hide_banners()
        w = SpeakWorker(assistant.speaker, self._ultima_resposta, parent=self)
        w.state_changed.connect(self._set_state)
        w.failed.connect(lambda t, m: (self._show_warning(f"{t}: {m}"), self._set_state("OCIOSO")))
        w.finished.connect(self._on_worker_finished)
        self._speak_worker = w
        w.start()

    def _on_history_clicked(self, item: QListWidgetItem) -> None:
        self._mostrar(self._resultados[item.data(Qt.UserRole)])

    def _mostrar(self, r: InteractionResult) -> None:
        """Exibe uma interação (a foto vem do frame em memória ou do JPEG salvo)."""
        if r.frame is not None:
            self.captured_view.set_image(frame_to_qimage(r.frame))
        elif r.image_jpeg:
            img = QImage.fromData(r.image_jpeg)
            if not img.isNull():
                self.captured_view.set_image(img)
            else:
                self.captured_view.clear_image("Imagem ilegível")
        else:
            self.captured_view.clear_image("Sem foto nesta pergunta")
        self._set_text(self.question_label, r.pergunta, "")
        self._set_text(self.answer_label, r.resposta, "")
        self._ultima_resposta = r.resposta
        self.repeat_button.setEnabled(not self.busy)

    # ====================================================== conversas salvas
    def _refresh_sidebar(self) -> None:
        self.sidebar.refresh(self._history_store.conversations(), self._conversa_id,
                             gravando=self.config.save_history)

    def _atualizar_do_disco(self) -> None:
        """Botão de atualizar: relê o histórico salvo e traz o que for novo.

        Se a conversa aberta tiver mais perguntas gravadas do que as exibidas (por exemplo,
        feitas por outra janela do app), ela é recarregada para incluí-las.
        """
        conversas = self._history_store.conversations()
        atual = next((c for c in conversas if c.id == self._conversa_id), None)
        if atual is not None and not self.busy and len(atual.entradas) > len(self._resultados):
            self._resultados = [self._resultado_de(e) for e in atual.entradas]
            self.history.clear()
            for i, r in enumerate(self._resultados):
                self.history.insertItem(0, self._item_para(r, i))
            self._mostrar(self._resultados[-1])
        self.sidebar.refresh(conversas, self._conversa_id, gravando=self.config.save_history)

    def _sync_assistant(self, assistant: Assistant) -> None:
        """Garante que o contexto enviado ao modelo é o da conversa que está na tela."""
        if assistant.session_id != self._conversa_id:
            turnos = [Turn(r.pergunta, r.resposta) for r in self._resultados]
            assistant.load_session(self._conversa_id, turnos)

    @staticmethod
    def _resultado_de(e) -> InteractionResult:
        try:
            jpeg = e.imagem.read_bytes() if e.imagem is not None else b""
        except OSError:
            jpeg = b""
        return InteractionResult(pergunta=e.pergunta, resposta=e.resposta, image_jpeg=jpeg,
                                 origem=e.origem, tempos=dict(e.tempos), timestamp=e.data_hora,
                                 sessao=e.sessao)

    def _abrir_conversa(self, session_id: str) -> None:
        """Carrega uma conversa salva; novas perguntas continuam nela."""
        if session_id == self._conversa_id:
            return
        conversa = next((c for c in self._history_store.conversations()
                         if c.id == session_id), None)
        if self.busy or conversa is None:
            self._refresh_sidebar()  # desfaz a seleção feita na lista
            return
        self._hide_banners()
        self._conversa_id = session_id
        self._resultados = [self._resultado_de(e) for e in conversa.entradas]
        self.history.clear()
        for i, r in enumerate(self._resultados):
            self.history.insertItem(0, self._item_para(r, i))
        self._mostrar(self._resultados[-1])
        self._set_state("OCIOSO")
        self._refresh_sidebar()

    def _confirmar_apagar(self, interacoes: int) -> bool:
        resposta = QMessageBox.question(
            self, "Apagar conversa",
            f"Apagar esta conversa ({interacoes} "
            f"{'pergunta' if interacoes == 1 else 'perguntas'}) e as fotos dela?\n\n"
            "Isso não pode ser desfeito.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return resposta == QMessageBox.Yes

    def _on_delete_conversation(self, session_id: str) -> None:
        if self.busy:
            return
        conversa = next((c for c in self._history_store.conversations()
                         if c.id == session_id), None)
        if conversa is None or not self._confirmar_apagar(len(conversa.entradas)):
            return
        self._history_store.delete_conversation(session_id)
        if session_id == self._conversa_id:
            self._on_clear()
        else:
            self._refresh_sidebar()

    def _on_clear(self) -> None:
        """Nova conversa: limpa a tela e o contexto; as conversas anteriores continuam salvas."""
        if self.busy:
            return
        self._conversa_id = new_session_id()
        self._resultados.clear()
        self.history.clear()
        self._ultima_resposta = None
        self.captured_view.clear_image()
        self._set_text(self.question_label, None, "Nenhuma pergunta ainda.")
        self._set_text(self.answer_label, None, "A resposta da IA aparecerá aqui.")
        self._hide_banners()
        self._set_state("OCIOSO")
        self._refresh_sidebar()

    # ============================================================ fechar
    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        """Para câmera, gravação e fala e espera as threads terminarem."""
        self.player.stop()
        if self._worker is not None:
            self._worker.stop_listening()
        self.camera_thread.stop()
        self.diagnostics_page.wait()
        for t in (self._worker, self._speak_worker, self.camera_thread):
            if t is not None and t.isRunning():
                t.wait(3000)
