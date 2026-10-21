"""Diagnóstico rápido do ambiente: `python -m visao_llm --diagnostico` e a página Diagnóstico.

Verifica chave da API, câmera, microfone, alto-falante e conexão com o provedor (OpenAI ou Gemini),
sem encerrar com exceção caso algo falhe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .audio import AudioRecorder, _sounddevice
from .camera import Camera
from .config import Config, nome_provedor
from .errors import AppError
from .openai_service import api_errors, build_client

OK, FALHA = "OK   ", "FALHA"


@dataclass(frozen=True)
class CheckResult:
    nome: str
    ok: bool
    detalhe: str


def _camera_padrao(config: Config) -> str:
    with Camera(config.camera_source) as cam:
        frame = cam.read()
    return f"fonte={config.camera_source}, resolução={frame.shape[1]}x{frame.shape[0]}"


def _alto_falante() -> str:
    sd = _sounddevice()
    return str(sd.query_devices(kind="output").get("name", "saída padrão"))


def _api(config: Config) -> str:
    client = build_client(config.with_overrides(max_retries=0, request_timeout=15.0))
    with api_errors("listar modelos"):
        ids = {m.id.removeprefix("models/") for m in client.models.list()}
    faltando = [m for m in (config.vision_model, config.stt_model, config.tts_model)
                if m not in ids]
    if faltando:
        return f"conectado; modelos não listados p/ sua conta: {', '.join(faltando)}"
    return "conectado; modelos configurados disponíveis"


def checks(config: Config, camera_check: Callable[[], str] | None = None
           ) -> list[tuple[str, Callable[[], str]]]:
    """Lista (nome, verificação) na ordem em que são executadas.

    `camera_check` substitui a abertura da câmera: a interface usa a câmera que já está aberta,
    pois abrir a mesma webcam duas vezes costuma falhar no Windows.
    """
    return [
        ("Chave da API", lambda: (config.require_api_key(), f"{config.provider}: lida do ambiente/.env")[1]),
        ("Câmera", camera_check or (lambda: _camera_padrao(config))),
        ("Microfone", lambda: AudioRecorder().check_available()),
        ("Alto-falante", _alto_falante),
        (f"Conexão com {nome_provedor(config.provider)}", lambda: _api(config)),
    ]


def run_check(nome: str, verificacao: Callable[[], str]) -> CheckResult:
    try:
        return CheckResult(nome, True, verificacao() or "")
    except AppError as exc:
        return CheckResult(nome, False, exc.mensagem)
    except Exception as exc:  # pragma: no cover - defensivo
        return CheckResult(nome, False, repr(exc))


def collect_diagnostics(config: Config, camera_check: Callable[[], str] | None = None
                        ) -> list[CheckResult]:
    return [run_check(nome, fn) for nome, fn in checks(config, camera_check)]


REQUISITO = {"Chave da API": "RNF01", "Câmera": "RF01", "Microfone": "RF02",
             "Alto-falante": "RF04"}


def run_diagnostics(config: Config) -> bool:
    resultados = collect_diagnostics(config)
    print("\nDiagnóstico — Visão e Interpretação do Ambiente com LLM\n")
    for r in resultados:
        rotulo = f"{r.nome} ({REQUISITO.get(r.nome, 'RF03')})"
        print(f"  [{OK if r.ok else FALHA}] {rotulo:<30} {r.detalhe}")
    tudo_ok = all(r.ok for r in resultados)
    print("\nTudo pronto!\n" if tudo_ok else "\nCorrija os itens com FALHA (veja o README).\n")
    return tudo_ok
