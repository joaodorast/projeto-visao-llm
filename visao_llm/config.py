"""Carregamento de configuração a partir de variáveis de ambiente / arquivo .env.

RNF01: a chave da API NUNCA fica no código-fonte. Ela é lida da variável de
ambiente OPENAI_API_KEY (que pode vir de um arquivo .env ignorado pelo git).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from dotenv import load_dotenv

from .errors import ConfigError

RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def _bool(valor: str | None, padrao: bool) -> bool:
    if valor is None or valor.strip() == "":
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _float(nome: str, valor: str | None, padrao: float) -> float:
    if valor is None or valor.strip() == "":
        return padrao
    try:
        return float(valor)
    except ValueError as exc:
        raise ConfigError(f"Valor inválido para {nome}: {valor!r} (esperado número).") from exc


def _int(nome: str, valor: str | None, padrao: int) -> int:
    return int(_float(nome, valor, padrao))


def parse_camera_source(valor: str | int | None) -> int | str:
    """'0' -> 0 (índice da webcam); qualquer outra coisa é caminho/URL de vídeo ou imagem."""
    if valor is None:
        return 0
    if isinstance(valor, int):
        return valor
    valor = valor.strip()
    if valor == "":
        return 0
    if valor.lstrip("-").isdigit():
        return int(valor)
    return valor


@dataclass(frozen=True)
class Config:
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None

    # Modelos (todos configuráveis pelo .env)
    vision_model: str = "gpt-4.1-mini"
    stt_model: str = "gpt-4o-mini-transcribe"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    language: str = "pt"

    # Rede
    request_timeout: float = 30.0
    max_retries: int = 2

    # Câmera
    camera_source: int | str = 0
    image_max_side: int = 1024

    # Microfone
    sample_rate: int = 16000
    max_record_seconds: float = 15.0
    silence_seconds: float = 1.3
    no_speech_timeout: float = 6.0

    # Voz
    tts_enabled: bool = True
    tts_offline_fallback: bool = True

    # Registro das interações (imagem + pergunta + resposta)
    save_history: bool = True
    history_dir: Path = RAIZ_PROJETO / "registros"
    log_dir: Path = RAIZ_PROJETO / "logs"

    def require_api_key(self) -> str:
        if not self.api_key or not self.api_key.strip():
            raise ConfigError(
                "Chave da OpenAI não configurada. Crie um arquivo .env (copie de "
                ".env.example) e defina OPENAI_API_KEY."
            )
        return self.api_key.strip()

    def with_overrides(self, **kwargs) -> "Config":
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})


def load_config(env_file: str | os.PathLike | None = None) -> Config:
    """Lê .env (se existir) e variáveis de ambiente e devolve um Config."""
    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(RAIZ_PROJETO / ".env", override=False)
        load_dotenv(override=False)  # .env no diretório atual, se houver

    env = os.environ.get
    padrao = Config()
    return Config(
        api_key=env("OPENAI_API_KEY"),
        base_url=env("OPENAI_BASE_URL") or None,
        vision_model=env("MODELO_VISAO") or padrao.vision_model,
        stt_model=env("MODELO_STT") or padrao.stt_model,
        tts_model=env("MODELO_TTS") or padrao.tts_model,
        tts_voice=env("VOZ_TTS") or padrao.tts_voice,
        language=env("IDIOMA") or padrao.language,
        request_timeout=_float("TIMEOUT_REQUISICAO", env("TIMEOUT_REQUISICAO"), padrao.request_timeout),
        max_retries=_int("TENTATIVAS_API", env("TENTATIVAS_API"), padrao.max_retries),
        camera_source=parse_camera_source(env("CAMERA")),
        image_max_side=_int("IMAGEM_LADO_MAX", env("IMAGEM_LADO_MAX"), padrao.image_max_side),
        max_record_seconds=_float("GRAVACAO_MAX_SEG", env("GRAVACAO_MAX_SEG"), padrao.max_record_seconds),
        silence_seconds=_float("SILENCIO_SEG", env("SILENCIO_SEG"), padrao.silence_seconds),
        no_speech_timeout=_float("SEM_FALA_SEG", env("SEM_FALA_SEG"), padrao.no_speech_timeout),
        tts_enabled=_bool(env("TTS_ATIVO"), padrao.tts_enabled),
        tts_offline_fallback=_bool(env("TTS_OFFLINE_FALLBACK"), padrao.tts_offline_fallback),
        save_history=_bool(env("SALVAR_HISTORICO"), padrao.save_history),
        history_dir=Path(env("PASTA_HISTORICO") or padrao.history_dir),
        log_dir=Path(env("PASTA_LOGS") or padrao.log_dir),
    )
