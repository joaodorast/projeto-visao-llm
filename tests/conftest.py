"""Fixtures e dublês (fakes) usados nos testes — nenhum teste usa rede ou hardware real."""

from __future__ import annotations

import os

import cv2
import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # o SDK da OpenAI usa httpx (ou o fork httpx2 em versões recentes)
    import httpx2 as httpx  # type: ignore
except ImportError:  # pragma: no cover
    import httpx  # type: ignore

from visao_llm.errors import CameraError, SpeakerError


def cena_mesa() -> np.ndarray:
    """Imagem sintética: 'mesa' com 'notebook' e 'garrafa'."""
    img = np.full((480, 640, 3), (225, 230, 235), np.uint8)
    cv2.rectangle(img, (0, 300), (640, 480), (60, 110, 160), -1)        # mesa
    cv2.rectangle(img, (120, 200), (330, 310), (40, 40, 40), -1)         # notebook
    cv2.rectangle(img, (420, 170), (460, 310), (200, 90, 30), -1)        # garrafa
    return img


@pytest.fixture
def frame() -> np.ndarray:
    return cena_mesa()


@pytest.fixture
def imagem_teste(tmp_path):
    caminho = tmp_path / "cena.jpg"
    cv2.imwrite(str(caminho), cena_mesa())
    return caminho


class FakeRecorder:
    def __init__(self, erro: Exception | None = None):
        self.erro = erro
        self.chamadas = 0

    def record(self, stop_event=None, on_level=None) -> bytes:
        self.chamadas += 1
        if on_level:
            on_level(0.2)
        if self.erro:
            raise self.erro
        return b"RIFF-fake-wav"


class FakeSTT:
    def __init__(self, texto="O que está sobre a mesa?", erro: Exception | None = None):
        self.texto, self.erro = texto, erro

    def transcribe(self, wav: bytes) -> str:
        if self.erro:
            raise self.erro
        return self.texto


class FakeVision:
    def __init__(self, resposta="Vejo um notebook e uma garrafa sobre a mesa.",
                 erro: Exception | None = None):
        self.resposta, self.erro = resposta, erro
        self.chamadas: list[tuple[bytes, str, tuple]] = []

    def ask(self, jpeg: bytes, pergunta: str, historico=()) -> str:
        self.chamadas.append((jpeg, pergunta, tuple(historico)))
        if self.erro:
            raise self.erro
        return self.resposta


class FakeSpeaker:
    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.falado: list[str] = []

    def speak(self, texto: str) -> str:
        if self.falhar:
            raise SpeakerError("Alto-falante desconectado.")
        self.falado.append(texto)
        return "fake"


def camera_quebrada():
    raise CameraError("Câmera indisponível.")


@pytest.fixture
def fakes():
    return dict(recorder=FakeRecorder(), stt=FakeSTT(), vision=FakeVision(),
                speaker=FakeSpeaker())


def http_response(status: int, json_body: dict | None = None) -> "httpx.Response":
    req = httpx.Request("POST", "https://api.openai.com/v1/test")
    return httpx.Response(status, json=json_body or {"error": {"message": "x"}}, request=req)
