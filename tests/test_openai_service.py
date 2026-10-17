"""RF02/RF03/RF04 — integração com a OpenAI; RNF02 — falhas de conexão e de API.

Usa o SDK oficial de verdade, mas com um transporte HTTP simulado (MockTransport):
nenhuma requisição sai para a internet.
"""

import base64
import json

import openai
import pytest

from conftest import http_response, httpx
from visao_llm.errors import APIError, NetworkError, NoSpeechError
from visao_llm.openai_service import (SpeechToText, TextToSpeech, Turn, VisionAssistant,
                                      api_errors)

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"


def cliente(handler) -> openai.OpenAI:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return openai.OpenAI(api_key="sk-teste", http_client=http, max_retries=0, timeout=5)


def resposta_chat(texto):
    return {
        "id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": texto}}],
    }


# ------------------------------------------------------------------ visão
def test_ct09_visao_envia_imagem_e_pergunta():
    """CT09: a requisição leva a pergunta transcrita + imagem em base64 (RF03)."""
    capturado = {}

    def handler(req):
        capturado["url"] = str(req.url)
        capturado["corpo"] = json.loads(req.content)
        return httpx.Response(200, json=resposta_chat("Vejo um notebook e uma garrafa azul."))

    va = VisionAssistant(cliente(handler), "gpt-teste")
    resp = va.ask(JPEG, "O que está sobre a mesa?", [Turn("Oi", "Olá!")])

    assert resp == "Vejo um notebook e uma garrafa azul."
    assert capturado["url"].endswith("/chat/completions")
    corpo = capturado["corpo"]
    assert corpo["model"] == "gpt-teste"
    ultima = corpo["messages"][-1]["content"]
    assert ultima[0] == {"type": "text", "text": "O que está sobre a mesa?"}
    url_img = ultima[1]["image_url"]["url"]
    assert url_img.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(url_img.split(",", 1)[1]) == JPEG
    assert corpo["messages"][0]["role"] == "system"
    assert [m["role"] for m in corpo["messages"]] == ["system", "user", "assistant", "user"]


def test_ct10_falha_de_conexao_vira_network_error():
    """CT10: internet caída -> NetworkError amigável (RNF02)."""
    def handler(req):
        raise httpx.ConnectError("Name or service not known", request=req)

    with pytest.raises(NetworkError, match="Sem conexão"):
        VisionAssistant(cliente(handler), "m").ask(JPEG, "?")


def test_ct11_timeout_vira_network_error():
    """CT11: API não responde a tempo -> NetworkError (tempo esgotado)."""
    def handler(req):
        raise httpx.ReadTimeout("timed out", request=req)

    with pytest.raises(NetworkError, match="Tempo esgotado"):
        VisionAssistant(cliente(handler), "m").ask(JPEG, "?")


@pytest.mark.parametrize("status,trecho", [
    (401, "Chave da API inválida"),
    (403, "permissão"),
    (404, "Modelo não encontrado"),
    (429, "Limite de uso"),
    (400, "recusou"),
    (500, "instável"),
    (503, "instável"),
])
def test_ct12_erros_http_da_api(status, trecho):
    """CT12: cada erro HTTP da API vira APIError com mensagem específica."""
    def handler(req):
        return httpx.Response(status, json={"error": {"message": "erro simulado"}})

    with pytest.raises(APIError, match=trecho):
        VisionAssistant(cliente(handler), "m").ask(JPEG, "?")


def test_resposta_vazia_do_modelo():
    def handler(req):
        return httpx.Response(200, json=resposta_chat(""))

    with pytest.raises(APIError, match="não retornou texto"):
        VisionAssistant(cliente(handler), "m").ask(JPEG, "?")


def test_api_errors_mapeia_excecoes_diretas():
    req = httpx.Request("POST", "https://api.openai.com/v1/x")
    with pytest.raises(NetworkError):
        with api_errors("teste"):
            raise openai.APIConnectionError(request=req)
    with pytest.raises(APIError, match="HTTP 418"):
        with api_errors("teste"):
            raise openai.APIStatusError("bule", response=http_response(418), body=None)


# -------------------------------------------------------------------- STT
def test_ct13_transcricao_envia_wav_e_idioma():
    """CT13: STT envia o áudio gravado (multipart) com idioma pt."""
    visto = {}

    def handler(req):
        visto["url"] = str(req.url)
        visto["corpo"] = req.content
        return httpx.Response(200, json={"text": "  O que você está vendo?  "})

    texto = SpeechToText(cliente(handler), "gpt-4o-mini-transcribe", "pt").transcribe(b"RIFFwav")
    assert texto == "O que você está vendo?"
    assert visto["url"].endswith("/audio/transcriptions")
    assert b"RIFFwav" in visto["corpo"] and b"pt" in visto["corpo"]


def test_transcricao_vazia_vira_no_speech():
    def handler(req):
        return httpx.Response(200, json={"text": ""})

    with pytest.raises(NoSpeechError):
        SpeechToText(cliente(handler), "m").transcribe(b"x")


# -------------------------------------------------------------------- TTS
def test_ct14_tts_retorna_pcm():
    """CT14: TTS pede formato PCM e devolve os bytes de áudio (RF04)."""
    visto = {}

    def handler(req):
        visto["corpo"] = json.loads(req.content)
        return httpx.Response(200, content=b"\x01\x02" * 50,
                              headers={"content-type": "audio/pcm"})

    pcm = TextToSpeech(cliente(handler), "gpt-4o-mini-tts", "alloy").synthesize("Olá")
    assert pcm == b"\x01\x02" * 50
    assert visto["corpo"]["response_format"] == "pcm"
    assert visto["corpo"]["input"] == "Olá"


def test_tts_sem_conexao():
    def handler(req):
        raise httpx.ConnectError("offline", request=req)

    with pytest.raises(NetworkError):
        TextToSpeech(cliente(handler), "tts-1").synthesize("Olá")
