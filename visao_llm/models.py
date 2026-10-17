"""Estruturas de dados compartilhadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

import numpy as np


class State(str, Enum):
    """Estados exibidos na interface (RF05)."""

    OCIOSO = "Pronto"
    OUVINDO = "Ouvindo…"
    CAPTURANDO = "Capturando imagem…"
    TRANSCREVENDO = "Transcrevendo fala…"
    PROCESSANDO = "Analisando a imagem…"
    FALANDO = "Falando resposta…"
    CONCLUIDO = "Resposta pronta"
    ERRO = "Erro"


def new_session_id() -> str:
    """Identificador de uma conversa (ordenável por data de criação)."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"


@dataclass
class InteractionResult:
    pergunta: str
    resposta: str
    image_jpeg: bytes
    frame: np.ndarray | None = field(default=None, repr=False)
    origem: str = "voz"  # "voz" ou "texto"
    tempos: dict[str, float] = field(default_factory=dict)
    aviso_voz: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    sessao: str = ""  # conversa a que a interação pertence
