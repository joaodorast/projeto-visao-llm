"""Hierarquia de erros da aplicação.

Cada erro carrega uma mensagem amigável (em português) que pode ser exibida
diretamente na interface, atendendo ao RNF02 (tratar falhas sem encerrar).
"""


class AppError(Exception):
    """Erro base: tudo que a aplicação sabe tratar e mostrar ao usuário."""

    #: Título curto exibido na interface.
    titulo = "Erro"

    def __init__(self, mensagem: str, *, detalhe: str | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhe = detalhe

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.mensagem


class ConfigError(AppError):
    titulo = "Configuração"


class CameraError(AppError):
    titulo = "Câmera"


class MicrophoneError(AppError):
    titulo = "Microfone"


class NoSpeechError(AppError):
    titulo = "Nenhuma fala detectada"


class NetworkError(AppError):
    titulo = "Conexão"


class APIError(AppError):
    titulo = "API OpenAI"


class SpeakerError(AppError):
    titulo = "Alto-falante"
