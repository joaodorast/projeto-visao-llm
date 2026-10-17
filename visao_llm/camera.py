"""Captura de imagens pela webcam (RF01) usando OpenCV.

A fonte pode ser:
  * um índice inteiro (0, 1, ...) -> webcam;
  * caminho de vídeo ou URL (rtsp/http) -> lido em loop;
  * caminho de imagem (.jpg/.png...) -> imagem estática (útil para testes e demonstrações).
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

import cv2
import numpy as np

from .errors import CameraError

log = logging.getLogger(__name__)

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class Camera:
    def __init__(self, source: int | str = 0):
        self.source = source
        self._cap: cv2.VideoCapture | None = None
        self._imagem_estatica: np.ndarray | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ util
    @property
    def _eh_imagem(self) -> bool:
        return isinstance(self.source, str) and Path(self.source).suffix.lower() in EXTENSOES_IMAGEM

    @property
    def _eh_arquivo_video(self) -> bool:
        return isinstance(self.source, str) and not self._eh_imagem and "://" not in self.source

    @property
    def is_open(self) -> bool:
        return self._imagem_estatica is not None or (self._cap is not None and self._cap.isOpened())

    # ---------------------------------------------------------------- ciclo
    def open(self) -> None:
        with self._lock:
            self._release_unlocked()
            if self._eh_imagem:
                img = cv2.imread(str(self.source))
                if img is None:
                    raise CameraError(f"Não foi possível abrir a imagem de teste: {self.source}")
                self._imagem_estatica = img
                log.info("Usando imagem estática como câmera: %s", self.source)
                return

            if self._eh_arquivo_video and not Path(self.source).exists():
                raise CameraError(f"Arquivo de vídeo não encontrado: {self.source}")

            cap = self._abrir_captura()
            if not cap.isOpened():
                cap.release()
                raise CameraError(
                    "Câmera indisponível. Verifique se a webcam está conectada, se outro "
                    f"programa não está usando-a e se o índice ({self.source}) está correto."
                )
            # buffer pequeno = frame mais atual possível no momento da pergunta
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._cap = cap
            log.info("Câmera aberta: %s", self.source)

    def _abrir_captura(self) -> cv2.VideoCapture:
        # No Windows, DirectShow abre a webcam mais rápido e com menos falhas que o MSMF.
        if sys.platform.startswith("win") and isinstance(self.source, int):
            cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if cap.isOpened():
                return cap
            cap.release()
        return cv2.VideoCapture(self.source)

    def read(self) -> np.ndarray:
        """Retorna um frame BGR. Lança CameraError se não for possível capturar."""
        with self._lock:
            if self._imagem_estatica is not None:
                return self._imagem_estatica.copy()
            if self._cap is None or not self._cap.isOpened():
                raise CameraError("A câmera não está aberta.")
            ok, frame = self._cap.read()
            if (not ok or frame is None) and self._eh_arquivo_video:
                # fim do vídeo: volta ao início
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
            if not ok or frame is None or frame.size == 0:
                raise CameraError("Falha ao ler imagem da câmera (dispositivo desconectado?).")
            return frame

    def close(self) -> None:
        with self._lock:
            self._release_unlocked()

    def _release_unlocked(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:  # pragma: no cover - defensivo
                pass
        self._cap = None
        self._imagem_estatica = None

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def resize_max_side(frame: np.ndarray, max_side: int) -> np.ndarray:
    h, w = frame.shape[:2]
    maior = max(h, w)
    if max_side <= 0 or maior <= max_side:
        return frame
    escala = max_side / maior
    return cv2.resize(frame, (int(round(w * escala)), int(round(h * escala))), interpolation=cv2.INTER_AREA)


def encode_jpeg(frame: np.ndarray, max_side: int = 1024, quality: int = 85) -> bytes:
    """Redimensiona (para economizar tokens/banda) e codifica o frame em JPEG."""
    if frame is None or frame.size == 0:
        raise CameraError("Imagem vazia: nada para enviar.")
    reduzido = resize_max_side(frame, max_side)
    ok, buf = cv2.imencode(".jpg", reduzido, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise CameraError("Falha ao codificar a imagem em JPEG.")
    return buf.tobytes()
