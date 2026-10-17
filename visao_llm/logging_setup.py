"""Configuração de logs: console + arquivo rotativo em logs/app.log."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMATO = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(pasta: Path, nivel: int = logging.INFO) -> None:
    raiz = logging.getLogger()
    if getattr(raiz, "_visao_llm_configurado", False):
        return
    raiz.setLevel(nivel)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(FORMATO, "%H:%M:%S"))
    raiz.addHandler(console)
    try:
        Path(pasta).mkdir(parents=True, exist_ok=True)
        arquivo = RotatingFileHandler(Path(pasta) / "app.log", maxBytes=1_000_000,
                                      backupCount=3, encoding="utf-8")
        arquivo.setFormatter(logging.Formatter(FORMATO))
        raiz.addHandler(arquivo)
    except OSError as exc:  # sem permissão de escrita: segue só com console
        raiz.warning("Log em arquivo desativado: %s", exc)
    # bibliotecas HTTP são verbosas demais em INFO
    for nome in ("httpx", "httpx2", "httpcore", "openai"):
        logging.getLogger(nome).setLevel(logging.WARNING)
    raiz._visao_llm_configurado = True  # type: ignore[attr-defined]
