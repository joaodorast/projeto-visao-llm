"""Orquestração do fluxo completo, independente da interface gráfica.

Voz:      ouvir -> capturar imagem -> transcrever -> modelo de visão -> exibir -> falar
Texto:    capturar imagem -> modelo de visão -> exibir -> falar
Conversa: repete o fluxo de voz sem novo clique, até o usuário pedir para encerrar
          (por voz, como "encerrar conversa", ou pelo botão)

A imagem é capturada logo que o usuário termina de falar, ou seja, no momento
em que a pergunta é feita (item 1 do "Funcionamento esperado").
"""

from __future__ import annotations

import logging
import re
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

import numpy as np

from .camera import encode_jpeg
from .errors import (AppError, CameraError, ConfigError, MicrophoneError, NoSpeechError,
                     SpeakerError)
from .models import InteractionResult, State, new_session_id
from .openai_service import Turn

log = logging.getLogger(__name__)


# ------------------------------------------------------------- contratos
class Recorder(Protocol):
    def record(self, stop_event: threading.Event | None = None,
               on_level: Callable[[float], None] | None = None,
               aguardar_fala: bool = False) -> bytes: ...


class Transcriber(Protocol):
    def transcribe(self, wav_bytes: bytes) -> str: ...


class Vision(Protocol):
    def ask(self, jpeg: bytes, pergunta: str, historico: Sequence[Turn] = ()) -> str: ...


class Voice(Protocol):
    def speak(self, texto: str) -> str: ...


class Store(Protocol):
    def save(self, resultado: InteractionResult): ...


#: Devolve o frame atual; None significa "câmera desligada pelo usuário" (pergunta sem foto).
FrameProvider = Callable[[], "np.ndarray | None"]


@dataclass
class Callbacks:
    """Ganchos opcionais para a interface acompanhar o progresso."""

    on_state: Callable[[State, str], None] | None = None
    on_level: Callable[[float], None] | None = None
    on_captured: Callable[[np.ndarray], None] | None = None
    on_question: Callable[[str], None] | None = None
    on_answer: Callable[[InteractionResult], None] | None = None
    #: modo conversa: erro em uma rodada (a conversa continua) e fim de cada rodada salva
    on_error: Callable[[AppError], None] | None = None
    on_turn_done: Callable[[], None] | None = None

    def state(self, estado: State, detalhe: str = "") -> None:
        if self.on_state:
            self.on_state(estado, detalhe)


# ------------------------------------------------------- fim da conversa por voz
FRASES_ENCERRAMENTO = (
    "encerrar conversa", "encerrar a conversa", "encerra a conversa", "encerra conversa",
    "encerre a conversa", "finalizar conversa", "finalizar a conversa", "finaliza a conversa",
    "terminar conversa", "terminar a conversa", "termina a conversa", "fim da conversa",
    "pode encerrar", "pode parar", "pode desligar", "parar de ouvir", "pare de ouvir",
    "para de ouvir", "parar a conversa", "pare a conversa", "era so isso", "e so isso",
    "por hoje e so", "ate logo", "ate mais", "ate a proxima",
)
PALAVRAS_ENCERRAMENTO = {"encerrar", "encerra", "encerre", "parar", "pare", "para", "chega",
                         "tchau", "sair", "fim", "finalizar", "terminar"}
MAX_PALAVRAS_ENCERRAMENTO = 7  # frases longas são perguntas, não pedidos para encerrar


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", sem_acento).split())


def pedido_de_encerramento(texto: str) -> bool:
    """True se a fala transcrita é um pedido para encerrar a conversa.

    Aceita frases curtas como "encerrar conversa", "pode parar", "tchau" ou "chega, obrigado";
    perguntas longas que só mencionam essas palavras não encerram.
    """
    normal = _normalizar(texto)
    palavras = normal.split()
    if not palavras or len(palavras) > MAX_PALAVRAS_ENCERRAMENTO:
        return False
    if any(frase in normal for frase in FRASES_ENCERRAMENTO):
        return True
    cortesia = {"obrigado", "obrigada", "valeu", "ok", "certo", "entao", "por", "favor", "agora"}
    resto = [p for p in palavras if p not in cortesia]
    return len(resto) == 1 and resto[0] in PALAVRAS_ENCERRAMENTO


class _EncerramentoPedido(Exception):
    """Usado dentro do modo conversa quando o usuário pede para encerrar falando."""


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
        self.session_id = new_session_id()

    # --------------------------------------------------------- API pública
    def ask_by_voice(self, stop_event: threading.Event | None = None,
                     cb: Callbacks | None = None, speak: bool = True) -> InteractionResult:
        cb = cb or Callbacks()
        return self._guard(cb, lambda: self._voice_flow(stop_event, cb, speak))

    def ask_by_text(self, pergunta: str, cb: Callbacks | None = None,
                    speak: bool = True) -> InteractionResult:
        cb = cb or Callbacks()
        return self._guard(cb, lambda: self._text_flow(pergunta, cb, speak))

    def converse(self, stop_event: threading.Event, cb: Callbacks | None = None,
                 speak: bool = True) -> str:
        """Modo conversa: ouve, responde e volta a ouvir, sem novo clique.

        Termina quando o usuário pede por voz ("encerrar conversa", "pode parar"...) e devolve
        "voz", ou quando `stop_event` é acionado (botão) e devolve "botao". Erros de uma rodada
        (rede, API, voz) são avisados por `cb.on_error` e a conversa continua; sem microfone ou
        sem chave não há como continuar, e o erro é repassado.
        """
        cb = cb or Callbacks()
        if self.recorder is None or self.stt is None:
            raise AppError("Entrada por voz não configurada.")
        while not stop_event.is_set():
            try:
                self._voice_flow(stop_event, cb, speak, conversa=True)
            except _EncerramentoPedido:
                if speak and self.speaker is not None:
                    cb.state(State.FALANDO)
                    try:
                        self.speaker.speak("Tudo bem, encerrando a conversa. Até mais!")
                    except SpeakerError:
                        pass
                cb.state(State.OCIOSO, "Conversa encerrada por voz.")
                return "voz"
            except NoSpeechError:
                continue  # silêncio, ruído ou parada pelo botão: volta a ouvir (ou sai)
            except (MicrophoneError, ConfigError) as exc:
                log.warning("Conversa interrompida: %s", exc.mensagem)
                cb.state(State.ERRO, exc.mensagem)
                raise
            except AppError as exc:
                self._avisar_erro(cb, exc)
            except Exception as exc:  # nunca deixar uma exceção desconhecida derrubar o app
                log.exception("Erro inesperado na conversa")
                self._avisar_erro(cb, AppError("Erro inesperado. Detalhes foram gravados no log.",
                                               detalhe=repr(exc)))
            else:
                if cb.on_turn_done:
                    cb.on_turn_done()
                stop_event.wait(0.25)  # deixa o eco da voz sumir antes de ouvir de novo
        cb.state(State.OCIOSO)
        return "botao"

    @staticmethod
    def _avisar_erro(cb: Callbacks, exc: AppError) -> None:
        log.warning("%s: %s (%s)", exc.titulo, exc.mensagem, exc.detalhe or "-")
        cb.state(State.ERRO, exc.mensagem)
        if cb.on_error:
            cb.on_error(exc)

    def clear_context(self) -> None:
        self.historico.clear()

    def new_session(self) -> str:
        """Começa uma conversa nova: zera o contexto e gera outro identificador."""
        self.clear_context()
        self.session_id = new_session_id()
        return self.session_id

    def load_session(self, session_id: str, turnos: Sequence[Turn] = ()) -> None:
        """Retoma uma conversa existente: as últimas trocas voltam como contexto do modelo."""
        self.historico.clear()
        limite = self.historico.maxlen or 0
        self.historico.extend(list(turnos)[-limite:] if limite else ())
        self.session_id = session_id

    # ------------------------------------------------------------- fluxos
    def _voice_flow(self, stop_event, cb: Callbacks, speak: bool,
                    conversa: bool = False) -> InteractionResult:
        if self.recorder is None or self.stt is None:
            raise AppError("Entrada por voz não configurada.")
        tempos: dict[str, float] = {}

        cb.state(State.OUVINDO, "fale quando quiser" if conversa else "")
        t = time.perf_counter()
        if conversa:
            wav = self.recorder.record(stop_event, cb.on_level, aguardar_fala=True)
        else:
            wav = self.recorder.record(stop_event, cb.on_level)
        tempos["gravacao"] = time.perf_counter() - t

        frame, jpeg = self._capture(cb, tempos)

        cb.state(State.TRANSCREVENDO)
        t = time.perf_counter()
        pergunta = self.stt.transcribe(wav)
        tempos["stt"] = time.perf_counter() - t
        if cb.on_question:
            cb.on_question(pergunta)
        if conversa and pedido_de_encerramento(pergunta):
            raise _EncerramentoPedido(pergunta)

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
        if frame is None:  # câmera desligada no app: a pergunta segue sem foto
            tempos["captura"] = time.perf_counter() - t
            return None, b""
        if getattr(frame, "size", 0) == 0:
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
                                      frame=frame, origem=origem, tempos=tempos,
                                      sessao=self.session_id)
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
