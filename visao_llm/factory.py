"""Monta os serviços concretos a partir da configuração."""

from __future__ import annotations

from .audio import AudioPlayer, AudioRecorder
from .config import Config
from .history import HistoryStore
from .openai_service import SpeechToText, TextToSpeech, VisionAssistant, build_client
from .pipeline import Assistant, FrameProvider
from .speaker import OfflineVoice, Speaker


def build_recorder(config: Config) -> AudioRecorder:
    return AudioRecorder(sample_rate=config.sample_rate, silence_seconds=config.silence_seconds,
                         max_seconds=config.max_record_seconds,
                         no_speech_timeout=config.no_speech_timeout)


def build_speaker(config: Config, client=None, player: AudioPlayer | None = None) -> Speaker | None:
    if not config.tts_enabled:
        return None
    tts = TextToSpeech(client, config.tts_model, config.tts_voice) if client is not None else None
    offline = OfflineVoice() if config.tts_offline_fallback else None
    return Speaker(tts, player=player, offline=offline)


def build_assistant(config: Config, frame_provider: FrameProvider,
                    player: AudioPlayer | None = None) -> Assistant:
    """Lança ConfigError se a chave da API não estiver configurada."""
    client = build_client(config)
    return Assistant(
        frame_provider=frame_provider,
        recorder=build_recorder(config),
        stt=SpeechToText(client, config.stt_model, config.language),
        vision=VisionAssistant(client, config.vision_model),
        speaker=build_speaker(config, client, player),
        store=HistoryStore(config.history_dir) if config.save_history else None,
        image_max_side=config.image_max_side,
    )
