"""RF02/RF04 com o Gemini — transcrição por chat com áudio e síntese de voz nativa.

Sem rede: o SDK usa MockTransport e a chamada HTTP nativa é simulada com monkeypatch.
"""

import base64
import io
import json
import urllib.error
import wave

import openai
import pytest

from conftest import httpx
from visao_llm import gemini_service
from visao_llm.config import Config
from visao_llm.errors import APIError, NetworkError, NoSpeechError
from visao_llm.factory import build_stt, build_tts, build_vision
from visao_llm.gemini_service import GeminiSpeechToText, GeminiTextToSpeech, extrair_pcm


def cliente(handler) -> openai.OpenAI:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return openai.OpenAI(api_key="chave", http_client=http, max_retries=0, timeout=5)


def resposta_chat(texto):
    return {"id": "1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": texto}}]}


def wav_bytes(pcm=b"\x01\x00" * 100, taxa=24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm)
    return buf.getvalue()


# -------------------------------------------------------------------- STT
def test_stt_envia_audio_como_input_audio():
    visto = {}

    def handler(req):
        visto["url"] = str(req.url)
        visto["corpo"] = json.loads(req.content)
        return httpx.Response(200, json=resposta_chat("  O que está na mesa?  "))

    texto = GeminiSpeechToText(cliente(handler), "gemini-x", "pt").transcribe(b"RIFFwav")
    assert texto == "O que está na mesa?"
    assert visto["url"].endswith("/chat/completions")
    partes = visto["corpo"]["messages"][0]["content"]
    audio = next(p for p in partes if p["type"] == "input_audio")["input_audio"]
    assert base64.b64decode(audio["data"]) == b"RIFFwav" and audio["format"] == "wav"
    assert visto["corpo"]["reasoning_effort"] == "low"


@pytest.mark.parametrize("retorno", ["", "[SEM_FALA]"])
def test_stt_sem_fala_vira_no_speech(retorno):
    def handler(req):
        return httpx.Response(200, json=resposta_chat(retorno))

    with pytest.raises(NoSpeechError):
        GeminiSpeechToText(cliente(handler), "m").transcribe(b"x")


def test_stt_erro_de_chave_vira_api_error():
    def handler(req):
        return httpx.Response(401, json={"error": {"message": "x"}})

    with pytest.raises(APIError, match="Chave da API inválida"):
        GeminiSpeechToText(cliente(handler), "m").transcribe(b"x")


# -------------------------------------------------------------------- TTS
def test_extrair_pcm_de_wav_e_de_pcm_bruto():
    assert extrair_pcm(wav_bytes(b"\x02\x00" * 10), "audio/wav") == b"\x02\x00" * 10
    assert extrair_pcm(b"\x03\x00" * 4, "audio/L16;rate=24000") == b"\x03\x00" * 4


def test_extrair_pcm_rejeita_taxa_inesperada():
    with pytest.raises(APIError, match="formato inesperado"):
        extrair_pcm(wav_bytes(taxa=16000), "audio/wav")


class RespostaFalsa:
    def __init__(self, corpo: dict):
        self._corpo = json.dumps(corpo).encode()

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def resposta_tts(wav: bytes) -> dict:
    return {"candidates": [{"content": {"parts": [{"inlineData": {
        "mimeType": "audio/wav", "data": base64.b64encode(wav).decode()}}]}}]}


def test_tts_chama_api_nativa_e_devolve_pcm(monkeypatch):
    visto = {}

    def urlopen(req, timeout):
        visto["url"] = req.full_url
        visto["chave"] = req.headers["X-goog-api-key"]
        visto["corpo"] = json.loads(req.data)
        return RespostaFalsa(resposta_tts(wav_bytes(b"\x05\x00" * 20)))

    monkeypatch.setattr(gemini_service.urllib.request, "urlopen", urlopen)
    pcm = GeminiTextToSpeech("chave-x", "gemini-tts", "Kore").synthesize("Olá")
    assert pcm == b"\x05\x00" * 20
    assert visto["url"].endswith("/models/gemini-tts:generateContent")
    assert visto["chave"] == "chave-x"
    assert visto["corpo"]["contents"][0]["parts"][0]["text"] == "Olá"
    assert visto["corpo"]["generationConfig"]["responseModalities"] == ["AUDIO"]


def test_tts_resposta_sem_audio(monkeypatch):
    monkeypatch.setattr(gemini_service.urllib.request, "urlopen",
                        lambda req, timeout: RespostaFalsa({"candidates": []}))
    with pytest.raises(APIError, match="áudio vazio"):
        GeminiTextToSpeech("k", "m").synthesize("Olá")


@pytest.mark.parametrize("status,trecho", [
    (401, "Chave da API inválida"), (403, "permissão"), (404, "Modelo não encontrado"),
    (429, "Limite de uso"), (400, "recusou"), (503, "instável"),
])
def test_tts_erros_http(monkeypatch, status, trecho):
    def urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, status, "x", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(gemini_service.urllib.request, "urlopen", urlopen)
    with pytest.raises(APIError, match=trecho):
        GeminiTextToSpeech("k", "m").synthesize("Olá")


def test_tts_sem_conexao_e_timeout(monkeypatch):
    def sem_rede(req, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(gemini_service.urllib.request, "urlopen", sem_rede)
    with pytest.raises(NetworkError, match="Sem conexão"):
        GeminiTextToSpeech("k", "m").synthesize("Olá")

    def lento(req, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr(gemini_service.urllib.request, "urlopen", lento)
    with pytest.raises(NetworkError, match="Tempo esgotado"):
        GeminiTextToSpeech("k", "m").synthesize("Olá")


# ---------------------------------------------------------------- fábrica
def test_fabrica_escolhe_servicos_do_gemini():
    cfg = Config(provider="gemini", api_key="k", tts_model="m-tts")
    cl = cliente(lambda req: httpx.Response(200, json=resposta_chat("x")))
    assert isinstance(build_stt(cfg, cl), GeminiSpeechToText)
    assert isinstance(build_tts(cfg, cl), GeminiTextToSpeech)
    assert build_vision(cfg, cl).reasoning_effort == "low"


def test_fabrica_openai_mantem_servicos_originais():
    from visao_llm.openai_service import SpeechToText, TextToSpeech
    cfg = Config(provider="openai", api_key="k")
    cl = cliente(lambda req: httpx.Response(200, json=resposta_chat("x")))
    assert isinstance(build_stt(cfg, cl), SpeechToText)
    assert isinstance(build_tts(cfg, cl), TextToSpeech)
    assert build_vision(cfg, cl).reasoning_effort is None
