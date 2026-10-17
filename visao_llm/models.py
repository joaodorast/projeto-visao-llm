"""Estruturas de dados compartilhadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

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
