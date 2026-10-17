"""Ponto de entrada: `python -m visao_llm` (ou `python main.py`)."""

from __future__ import annotations

import argparse
import os
import sys

from .config import PROVEDORES, load_config, parse_camera_source
from .errors import ConfigError
from .logging_setup import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="visao_llm",
        description="Assistente que vê pela webcam e responde perguntas por voz usando a OpenAI ou o Gemini.")
    parser.add_argument("--camera", help="índice da webcam (0, 1…) ou caminho de vídeo/imagem")
    parser.add_argument("--modelo", help="modelo de visão (sobrescreve MODELO_VISAO)")
    parser.add_argument("--provedor", choices=PROVEDORES,
                        help="provedor de LLM (sobrescreve PROVEDOR do .env)")
    parser.add_argument("--sem-voz", action="store_true", help="não falar as respostas (TTS off)")
    parser.add_argument("--diagnostico", action="store_true",
                        help="verifica câmera, microfone, chave e conexão e sai")
    parser.add_argument("--env", help="caminho de um arquivo .env alternativo")
    args = parser.parse_args(argv)

    if args.provedor:
        os.environ["PROVEDOR"] = args.provedor
    try:
        config = load_config(args.env)
    except ConfigError as exc:
        print(f"Erro de configuração: {exc.mensagem}", file=sys.stderr)
        return 2
    config = config.with_overrides(
        camera_source=parse_camera_source(args.camera) if args.camera is not None else None,
        vision_model=args.modelo,
        tts_enabled=False if args.sem_voz else None,
    )
    setup_logging(config.log_dir)

    if args.diagnostico:
        from .diagnostics import run_diagnostics
        return 0 if run_diagnostics(config) else 1

    from .gui.app import run_gui
    return run_gui(config)


if __name__ == "__main__":
    sys.exit(main())
