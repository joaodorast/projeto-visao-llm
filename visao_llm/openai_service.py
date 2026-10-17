"""Integração com a API da OpenAI: STT (RF02), visão multimodal (RF03) e TTS (RF04).

O SDK também é usado com o Gemini (endpoint compatível): VisionAssistant e api_errors
são compartilhados com gemini_service.

Todas as exceções do SDK são convertidas em NetworkError / APIError com
mensagens claras, para a interface tratá-las sem encerrar (RNF02).
"""

from __future__ import annotations

import base64
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Sequence

import openai
from openai import OpenAI

from .config import Config
from .errors import APIError, AppError, NetworkError, NoSpeechError

log = logging.getLogger(__name__)

TTS_SAMPLE_RATE = 24000  # formato "pcm" da OpenAI: 24 kHz, 16-bit, mono

SYSTEM_PROMPT = """\
Você é o "olho" de um robô assistente. A cada pergunta você recebe UMA foto \
tirada pela webcam do robô no exato momento em que o usuário perguntou.

Regras:
- Responda em português do Brasil, de forma natural, como quem está vendo a cena.
- Baseie a resposta no que está visível na imagem. Não invente objetos.
- Se a imagem não permitir responder (escura, desfocada, objeto fora do quadro), \
diga isso com franqueza e sugira o que o usuário pode fazer (ex.: aproximar o objeto).
- Seja breve: no máximo 3 frases curtas, pois a resposta será falada em voz alta.
- Não use markdown, listas, emojis nem símbolos; escreva números por extenso quando curtos.
- Se a pergunta não tiver relação com a imagem, responda normalmente e de forma breve.
"""


def build_client(config: Config) -> OpenAI:
    kwargs = dict(api_key=config.require_api_key(), timeout=config.request_timeout,
                  max_retries=config.max_retries)
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


@contextmanager
def api_errors(operacao: str) -> Iterator[None]:
    """Converte exceções do SDK OpenAI em erros da aplicação."""
    try:
        yield
    except AppError:
        raise
    except openai.APITimeoutError as exc:
        raise NetworkError(f"Tempo esgotado ao {operacao}. Verifique sua conexão e tente de novo.",
                           detalhe=str(exc)) from exc
    except openai.APIConnectionError as exc:
        raise NetworkError(f"Sem conexão com a API ao {operacao}. Verifique a internet.",
                           detalhe=str(exc)) from exc
    except openai.AuthenticationError as exc:
        raise APIError("Chave da API inválida ou revogada. Confira a chave do provedor no .env.",
                       detalhe=str(exc)) from exc
    except openai.PermissionDeniedError as exc:
        raise APIError("Sua conta não tem permissão para este recurso/modelo.",
                       detalhe=str(exc)) from exc
    except openai.RateLimitError as exc:
        raise APIError("Limite de uso da API atingido (ou sem créditos). Aguarde e tente novamente.",
                       detalhe=str(exc)) from exc
    except openai.NotFoundError as exc:
        raise APIError("Modelo não encontrado. Confira os nomes dos modelos no .env.",
                       detalhe=str(exc)) from exc
    except openai.BadRequestError as exc:
        raise APIError(f"A API recusou a requisição ao {operacao}.", detalhe=str(exc)) from exc
    except openai.InternalServerError as exc:
        raise APIError("A API está instável no momento (erro no servidor). Tente novamente.",
                       detalhe=str(exc)) from exc
    except openai.APIStatusError as exc:
        raise APIError(f"Erro da API ao {operacao} (HTTP {exc.status_code}).",
                       detalhe=str(exc)) from exc
    except openai.OpenAIError as exc:
        raise APIError(f"Erro inesperado da API ao {operacao}.", detalhe=str(exc)) from exc


# ----------------------------------------------------------------------- STT
class SpeechToText:
    def __init__(self, client: OpenAI, model: str, language: str = "pt"):
        self.client = client
        self.model = model
        self.language = language

    def transcribe(self, wav_bytes: bytes) -> str:
        with api_errors("transcrever o áudio"):
            resposta = self.client.audio.transcriptions.create(
                model=self.model,
                file=("pergunta.wav", wav_bytes, "audio/wav"),
                language=self.language,
            )
        texto = (getattr(resposta, "text", None) or "").strip()
        if not texto:
            raise NoSpeechError("Não entendi a pergunta. Pode repetir?")
        return texto


# -------------------------------------------------------------------- Visão
@dataclass
class Turn:
    pergunta: str
    resposta: str


class VisionAssistant:
    def __init__(self, client: OpenAI, model: str, max_tokens: int = 1000,
                 system_prompt: str = SYSTEM_PROMPT, reasoning_effort: str | None = None):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        #: Nível de raciocínio do modelo ("low"…); None mantém o padrão do provedor.
        self.reasoning_effort = reasoning_effort

    def build_messages(self, jpeg: bytes, pergunta: str,
                       historico: Sequence[Turn] = ()) -> list[dict]:
        b64 = base64.b64encode(jpeg).decode("ascii")
        mensagens: list[dict] = [{"role": "system", "content": self.system_prompt}]
        # Contexto textual das últimas trocas (sem reenviar imagens antigas)
        for turno in historico:
            mensagens.append({"role": "user", "content": turno.pergunta})
            mensagens.append({"role": "assistant", "content": turno.resposta})
        mensagens.append({
            "role": "user",
            "content": [
                {"type": "text", "text": pergunta},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "auto"}},
            ],
        })
        return mensagens

    def ask(self, jpeg: bytes, pergunta: str, historico: Sequence[Turn] = ()) -> str:
        mensagens = self.build_messages(jpeg, pergunta, historico)
        extras = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        with api_errors("consultar o modelo de visão"):
            resposta = self.client.chat.completions.create(
                model=self.model,
                messages=mensagens,
                max_completion_tokens=self.max_tokens,
                **extras,
            )
        try:
            texto = (resposta.choices[0].message.content or "").strip()
        except (AttributeError, IndexError) as exc:
            raise APIError("Resposta da API em formato inesperado.", detalhe=repr(resposta)) from exc
        if not texto:
            raise APIError("O modelo não retornou texto. Tente reformular a pergunta.")
        return texto


# ----------------------------------------------------------------------- TTS
class TextToSpeech:
    def __init__(self, client: OpenAI, model: str, voice: str = "alloy"):
        self.client = client
        self.model = model
        self.voice = voice

    def synthesize(self, texto: str) -> bytes:
        """Retorna PCM 16-bit mono a 24 kHz."""
        kwargs = dict(model=self.model, voice=self.voice, input=texto, response_format="pcm")
        if "gpt-4o" in self.model or self.model.startswith("gpt-"):
            kwargs["instructions"] = "Fale em português do Brasil, com tom amigável e claro."
        with api_errors("gerar o áudio da resposta"):
            resposta = self.client.audio.speech.create(**kwargs)
            dados = resposta.content if hasattr(resposta, "content") else resposta.read()
        if not dados:
            raise APIError("A API de voz retornou áudio vazio.")
        return dados
