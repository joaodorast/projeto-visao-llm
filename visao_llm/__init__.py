"""Visão e Interpretação do Ambiente com LLM — Projeto 1 de Engenharia de Software."""

__version__ = "1.0.0"

import os as _os

# Silencia os avisos internos do OpenCV ao procurar/reconectar a webcam.
_os.environ.setdefault("OPENCV_LOG_LEVEL", "OFF")
_os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_OBSENSOR", "0")
