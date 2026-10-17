"""Integração com o Gemini: STT (RF02) e TTS (RF04).

A visão (RF03) reutiliza `openai_service.VisionAssistant`, pois o Gemini expõe um
endpoint compatível com o SDK da OpenAI. Esse endpoint não oferece transcrição nem
síntese de voz dedicadas, então:

* STT: o áudio vai como `input_audio` em uma chamada de chat pedindo a transcrição;
* TTS: usa a API nativa `generateContent` com modalidade de resposta AUDIO.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import socket
import urllib.error
import urllib.request
import wave

from openai import OpenAI

from .errors import APIError, NetworkError, NoSpeechError
from .openai_service import TTS_SAMPLE_RATE, api_errors

log = logging.getLogger(__name__)

API_NATIVA = "https://generativelanguage.googleapis.com/v1beta"
MARCADOR_SEM_FALA = "[SEM_FALA]"

PROMPT_STT = (
    "Transcreva fielmente a fala deste áudio, no idioma '{idioma}'. Responda somente com "
    f"a transcrição, sem comentários. Se não houver fala, responda exatamente {MARCADOR_SEM_FALA}."
)


# ----------------------------------------------------------------------- STT
class GeminiSpeechToText:
    def __init__(self, client: OpenAI, model: str, language: str = "pt",
                 reasoning_effort: str | None = "low"):
        self.client = client
        self.model = model
        self.language = language
        self.reasoning_effort = reasoning_effort

    def transcribe(self, wav_bytes: bytes) -> str:
        audio = base64.b64encode(wav_bytes).decode("ascii")
        extras = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        with api_errors("transcrever o áudio"):
            resposta = self.client.chat.completions.create(
                model=self.model,
                max_completion_tokens=500,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": PROMPT_STT.format(idioma=self.language)},
                    {"type": "input_audio", "input_audio": {"data": audio, "format": "wav"}},
                ]}],
                **extras,
            )
        try:
            texto = (resposta.choices[0].message.content or "").strip()
        except (AttributeError, IndexError) as exc:
            raise APIError("Resposta da API em formato inesperado.", detalhe=repr(resposta)) from exc
        if not texto or MARCADOR_SEM_FALA in texto:
            raise NoSpeechError("Não entendi a pergunta. Pode repetir?")
        return texto


# ----------------------------------------------------------------------- TTS
def extrair_pcm(dados: bytes, mime: str) -> bytes:
    """Converte o áudio devolvido pela API em PCM 16-bit mono a 24 kHz.

    Aceita WAV (com cabeçalho) ou PCM bruto (`audio/L16;rate=24000`).
    """
    if not mime.startswith("audio/wav") and not mime.startswith("audio/x-wav"):
        return dados
    try:
        with wave.open(io.BytesIO(dados)) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, TTS_SAMPLE_RATE):
                raise APIError("A API de voz retornou áudio em formato inesperado.",
                               detalhe=str(wav.getparams()))
            return wav.readframes(wav.getnframes())
    except wave.Error as exc:
        raise APIError("A API de voz retornou áudio inválido.", detalhe=str(exc)) from exc


class GeminiTextToSpeech:
    """Mesma interface de `openai_service.TextToSpeech`: `synthesize(texto) -> PCM 24 kHz`."""

    def __init__(self, api_key: str, model: str, voice: str = "Kore", timeout: float = 30.0,
                 base_url: str = API_NATIVA):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    def synthesize(self, texto: str) -> bytes:
        corpo = {
            "contents": [{"parts": [{"text": texto}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.voice}}},
            },
        }
        resposta = self._post(f"{self.base_url}/models/{self.model}:generateContent", corpo)
        try:
            parte = resposta["candidates"][0]["content"]["parts"][0]["inlineData"]
            dados = base64.b64decode(parte["data"])
            mime = parte.get("mimeType", "")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise APIError("A API de voz retornou áudio vazio.", detalhe=repr(resposta)[:300]) from exc
        pcm = extrair_pcm(dados, mime)
        if not pcm:
            raise APIError("A API de voz retornou áudio vazio.")
        return pcm

    def _post(self, url: str, corpo: dict) -> dict:
        requisicao = urllib.request.Request(
            url, data=json.dumps(corpo).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        operacao = "gerar o áudio da resposta"
        try:
            with urllib.request.urlopen(requisicao, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as exc:
            raise self._erro_http(exc, operacao) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise NetworkError(f"Tempo esgotado ao {operacao}. Verifique sua conexão e tente de novo.",
                               detalhe=str(exc)) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise NetworkError(f"Tempo esgotado ao {operacao}. Verifique sua conexão e tente de novo.",
                                   detalhe=str(exc)) from exc
            raise NetworkError(f"Sem conexão com a API ao {operacao}. Verifique a internet.",
                               detalhe=str(exc)) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise APIError("Resposta da API em formato inesperado.", detalhe=str(exc)) from exc

    @staticmethod
    def _erro_http(exc: urllib.error.HTTPError, operacao: str) -> APIError:
        detalhe = exc.read()[:300].decode("utf-8", "replace")
        if exc.code in (400, 401):
            if exc.code == 401 or "API key" in detalhe:
                return APIError("Chave da API inválida ou revogada. Confira a chave do provedor no .env.",
                                detalhe=detalhe)
            return APIError(f"A API recusou a requisição ao {operacao}.", detalhe=detalhe)
        if exc.code == 403:
            return APIError("Sua conta não tem permissão para este recurso/modelo.", detalhe=detalhe)
        if exc.code == 404:
            return APIError("Modelo não encontrado. Confira os nomes dos modelos no .env.", detalhe=detalhe)
        if exc.code == 429:
            return APIError("Limite de uso da API atingido (ou sem créditos). Aguarde e tente novamente.",
                            detalhe=detalhe)
        if exc.code >= 500:
            return APIError("A API está instável no momento (erro no servidor). Tente novamente.",
                            detalhe=detalhe)
        return APIError(f"Erro da API ao {operacao} (HTTP {exc.code}).", detalhe=detalhe)
