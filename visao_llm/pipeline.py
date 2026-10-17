"""Orquestração do fluxo completo, independente da interface gráfica.

Voz:   ouvir -> capturar imagem -> transcrever -> modelo de visão -> exibir -> falar
Texto: capturar imagem -> modelo de visão -> exibir -> falar

A imagem é capturada logo que o usuário termina de falar, ou seja, no momento
em que a pergunta é feita (item 1 do "Funcionamento esperado").
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

import numpy as np

from .camera import encode_jpeg
from .errors import AppError, CameraError, SpeakerError
from .models import InteractionResult, State
from .openai_service import Turn

log = logging.getLogger(__name__)


# ------------------------------------------------------------- contratos
class Recorder(Protocol):
    def record(self, stop_event: threading.Event | None = None,
               on_level: Callable[[float], None] | None = None) -> bytes: ...


class Transcriber(Protocol):
    def transcribe(self, wav_bytes: bytes) -> str: ...


class Vision(Protocol):
    def ask(self, jpeg: bytes, pergunta: str, historico: Sequence[Turn] = ()) -> str: ...


class Voice(Protocol):
    def speak(self, texto: str) -> str: ...


class Store(Protocol):
    def save(self, resultado: InteractionResult): ...


FrameProvider = Callable[[], np.ndarray]


@dataclass
class Callbacks:
    """Ganchos opcionais para a interface acompanhar o progresso."""

    on_state: Callable[[State, str], None] | None = None
    on_level: Callable[[float], None] | None = None
    on_captured: Callable[[np.ndarray], None] | None = None
    on_question: Callable[[str], None] | None = None
    on_answer: Callable[[InteractionResult], None] | None = None

    def state(self, estado: State, detalhe: str = "") -> None:
        if self.on_state:
            self.on_state(estado, detalhe)


class Assistant:
    def __init__(self, frame_provider: FrameProvider, recorder: Recorder | None,
                 stt: Transcriber | None, vision: Vision, speaker: Voice | None = None,
                 store: Store | None = None, image_max_side: int = 1024,
                 context_turns: int = 3):
        self.frame_provider = frame_provider
        self.recorder = recorder
        self.stt = stt
        self.vision = vision
        self.speaker = speaker
        self.store = store
        self.image_max_side = image_max_side
        self.historico: deque[Turn] = deque(maxlen=max(0, context_turns))

    # --------------------------------------------------------- API pública
    def ask_by_voice(self, stop_event: threading.Event | None = None,
                     cb: Callbacks | None = None, speak: bool = True) -> InteractionResult:
        cb = cb or Callbacks()
        return self._guard(cb, lambda: self._voice_flow(stop_event, cb, speak))

    def ask_by_text(self, pergunta: str, cb: Callbacks | None = None,
                    speak: bool = True) -> InteractionResult:
        cb = cb or Callbacks()
        return self._guard(cb, lambda: self._text_flow(pergunta, cb, speak))

    def clear_context(self) -> None:
        self.historico.clear()

    # ------------------------------------------------------------- fluxos
    def _voice_flow(self, stop_event, cb: Callbacks, speak: bool) -> InteractionResult:
        if self.recorder is None or self.stt is None:
            raise AppError("Entrada por voz não configurada.")
        tempos: dict[str, float] = {}

        cb.state(State.OUVINDO)
        t = time.perf_counter()
        wav = self.recorder.record(stop_event, cb.on_level)
        tempos["gravacao"] = time.perf_counter() - t

        frame, jpeg = self._capture(cb, tempos)

        cb.state(State.TRANSCREVENDO)
        t = time.perf_counter()
        pergunta = self.stt.transcribe(wav)
        tempos["stt"] = time.perf_counter() - t
        if cb.on_question:
            cb.on_question(pergunta)

        return self._answer(pergunta, frame, jpeg, "voz", cb, speak, tempos)

    def _text_flow(self, pergunta: str, cb: Callbacks, speak: bool) -> InteractionResult:
        pergunta = (pergunta or "").strip()
        if not pergunta:
            raise AppError("Digite uma pergunta antes de enviar.")
        tempos: dict[str, float] = {}
        if cb.on_question:
            cb.on_question(pergunta)
        frame, jpeg = self._capture(cb, tempos)
        return self._answer(pergunta, frame, jpeg, "texto", cb, speak, tempos)

    def _capture(self, cb: Callbacks, tempos: dict[str, float]):
        cb.state(State.CAPTURANDO)
        t = time.perf_counter()
        try:
            frame = self.frame_provider()
        except CameraError:
            raise
        except Exception as exc:
            raise CameraError("Falha ao capturar a imagem da câmera.", detalhe=str(exc)) from exc
        if frame is None or getattr(frame, "size", 0) == 0:
            raise CameraError("A câmera não forneceu imagem. Verifique a conexão da webcam.")
        frame = frame.copy()
        jpeg = encode_jpeg(frame, self.image_max_side)
        tempos["captura"] = time.perf_counter() - t
        if cb.on_captured:
            cb.on_captured(frame)
        return frame, jpeg

    def _answer(self, pergunta: str, frame, jpeg: bytes, origem: str, cb: Callbacks,
                speak: bool, tempos: dict[str, float]) -> InteractionResult:
        cb.state(State.PROCESSANDO)
        t = time.perf_counter()
        resposta = self.vision.ask(jpeg, pergunta, tuple(self.historico))
        tempos["llm"] = time.perf_counter() - t

        self.historico.append(Turn(pergunta, resposta))
        resultado = InteractionResult(pergunta=pergunta, resposta=resposta, image_jpeg=jpeg,
                                      frame=frame, origem=origem, tempos=tempos)
        if cb.on_answer:
            cb.on_answer(resultado)

        if speak and self.speaker is not None:
            cb.state(State.FALANDO)
            t = time.perf_counter()
            try:
                self.speaker.speak(resposta)
            except SpeakerError as exc:
                # A resposta textual já foi exibida: a falha de voz não é fatal.
                resultado.aviso_voz = exc.mensagem
                log.warning("Resposta exibida, mas não falada: %s", exc.mensagem)
            tempos["tts"] = time.perf_counter() - t

        if self.store is not None:
            self.store.save(resultado)

        cb.state(State.CONCLUIDO, resultado.aviso_voz or "")
        log.info("Interação concluída (%s): %r -> %r | tempos=%s", origem, pergunta,
                 resposta, {k: round(v, 2) for k, v in tempos.items()})
        return resultado

    # ---------------------------------------------------------- proteção
    @staticmethod
    def _guard(cb: Callbacks, fn: Callable[[], InteractionResult]) -> InteractionResult:
        try:
            return fn()
        except AppError as exc:
            log.warning("%s: %s (%s)", exc.titulo, exc.mensagem, exc.detalhe or "-")
            cb.state(State.ERRO, exc.mensagem)
            raise
        except Exception as exc:  # nunca deixar uma exceção desconhecida derrubar o app
            log.exception("Erro inesperado no fluxo")
            erro = AppError("Erro inesperado. Detalhes foram gravados no log.", detalhe=repr(exc))
            cb.state(State.ERRO, erro.mensagem)
            raise erro from exc
