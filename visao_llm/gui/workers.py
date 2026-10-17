"""Threads de trabalho: mantêm a interface responsiva (RNF03).

* CameraThread: lê a webcam continuamente e guarda o frame mais recente,
  reconectando sozinha se a câmera cair (RNF02).
* InteractionWorker: executa o fluxo pergunta->resposta fora da thread da GUI.
* SpeakWorker: repete a fala de uma resposta.
"""

from __future__ import annotations

import logging
import threading
import time

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from ..camera import Camera
from ..errors import AppError, CameraError
from ..models import InteractionResult, State
from ..pipeline import Assistant, Callbacks

log = logging.getLogger(__name__)


def frame_to_qimage(frame: np.ndarray) -> QImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(bool, str)

    def __init__(self, source: int | str, fps: float = 25.0, retry_seconds: float = 3.0,
                 parent=None):
        super().__init__(parent)
        self.camera = Camera(source)
        self.intervalo = 1.0 / fps
        self.retry_seconds = retry_seconds
        self._parar = threading.Event()
        self._lock = threading.Lock()
        self._ultimo: np.ndarray | None = None
        self._ultimo_ts = 0.0
        self._ok: bool | None = None

    # ------------------------------------------------------------------ API
    def latest_frame(self) -> np.ndarray:
        """Frame mais recente (chamado a partir da thread de interação)."""
        with self._lock:
            frame, ts = self._ultimo, self._ultimo_ts
        if frame is None or time.monotonic() - ts > 2.0:
            raise CameraError("Câmera indisponível no momento. Verifique a webcam; "
                              "o app tentará reconectar automaticamente.")
        return frame.copy()

    def stop(self) -> None:
        self._parar.set()

    # ------------------------------------------------------------------ loop
    def _set_status(self, ok: bool, msg: str) -> None:
        if ok != self._ok:
            self._ok = ok
            self.status_changed.emit(ok, msg)

    def run(self) -> None:
        while not self._parar.is_set():
            if not self.camera.is_open:
                try:
                    self.camera.open()
                    self._set_status(True, f"Câmera conectada ({self.camera.source})")
                except CameraError as exc:
                    self._set_status(False, exc.mensagem)
                    self._parar.wait(self.retry_seconds)
                    continue
            try:
                frame = self.camera.read()
            except CameraError as exc:
                log.warning("Leitura da câmera falhou: %s", exc.mensagem)
                self.camera.close()
                with self._lock:
                    self._ultimo = None
                self._set_status(False, exc.mensagem)
                self._parar.wait(self.retry_seconds)
                continue
            with self._lock:
                self._ultimo = frame
                self._ultimo_ts = time.monotonic()
            self.frame_ready.emit(frame_to_qimage(frame))
            self._parar.wait(self.intervalo)
        self.camera.close()


class InteractionWorker(QThread):
    state_changed = pyqtSignal(str, str)          # nome do State, detalhe
    level_changed = pyqtSignal(float)
    image_captured = pyqtSignal(QImage)
    question_ready = pyqtSignal(str)
    answer_ready = pyqtSignal(object)             # InteractionResult
    failed = pyqtSignal(str, str)                 # título, mensagem

    def __init__(self, assistant: Assistant, pergunta_texto: str | None = None,
                 speak: bool = True, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.pergunta_texto = pergunta_texto
        self.speak = speak
        self.stop_event = threading.Event()

    def stop_listening(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        cb = Callbacks(
            on_state=lambda s, d: self.state_changed.emit(s.name, d),
            on_level=self.level_changed.emit,
            on_captured=lambda f: self.image_captured.emit(frame_to_qimage(f)),
            on_question=self.question_ready.emit,
            on_answer=self.answer_ready.emit,
        )
        try:
            if self.pergunta_texto is not None:
                self.assistant.ask_by_text(self.pergunta_texto, cb, speak=self.speak)
            else:
                self.assistant.ask_by_voice(self.stop_event, cb, speak=self.speak)
        except AppError as exc:
            self.failed.emit(exc.titulo, exc.mensagem)
        except Exception as exc:  # pragma: no cover - o pipeline já embrulha
            log.exception("Falha inesperada no worker")
            self.failed.emit("Erro", repr(exc))


class SpeakWorker(QThread):
    state_changed = pyqtSignal(str, str)
    failed = pyqtSignal(str, str)

    def __init__(self, speaker, texto: str, parent=None):
        super().__init__(parent)
        self.speaker = speaker
        self.texto = texto

    def run(self) -> None:
        self.state_changed.emit(State.FALANDO.name, "")
        try:
            self.speaker.speak(self.texto)
            self.state_changed.emit(State.CONCLUIDO.name, "")
        except AppError as exc:
            self.failed.emit(exc.titulo, exc.mensagem)


__all__ = ["CameraThread", "InteractionWorker", "SpeakWorker", "frame_to_qimage",
           "InteractionResult"]
