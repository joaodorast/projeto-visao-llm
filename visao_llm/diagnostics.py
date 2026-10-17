"""Diagnóstico rápido do ambiente: `python -m visao_llm --diagnostico`.

Verifica chave da API, câmera, microfone, alto-falante e conexão com o provedor (OpenAI ou Gemini),
sem encerrar com exceção caso algo falhe.
"""

from __future__ import annotations

from .audio import AudioRecorder, _sounddevice
from .camera import Camera
from .config import Config
from .errors import AppError
from .openai_service import api_errors, build_client

OK, FALHA = "OK   ", "FALHA"


def run_diagnostics(config: Config) -> bool:
    resultados: list[tuple[str, bool, str]] = []

    def checar(nome: str, fn) -> None:
        try:
            detalhe = fn() or ""
            resultados.append((nome, True, detalhe))
        except AppError as exc:
            resultados.append((nome, False, exc.mensagem))
        except Exception as exc:  # pragma: no cover - defensivo
            resultados.append((nome, False, repr(exc)))

    checar(f"Chave da API {config.provider} (RNF01)", lambda: (config.require_api_key(), "lida do ambiente/.env")[1])

    def camera():
        with Camera(config.camera_source) as cam:
            frame = cam.read()
        return f"fonte={config.camera_source!r}, resolução={frame.shape[1]}x{frame.shape[0]}"

    checar("Câmera (RF01)", camera)
    checar("Microfone (RF02)", lambda: AudioRecorder().check_available())

    def alto_falante():
        sd = _sounddevice()
        return str(sd.query_devices(kind="output").get("name", "saída padrão"))

    checar("Alto-falante (RF04)", alto_falante)

    def api():
        client = build_client(config.with_overrides(max_retries=0, request_timeout=15.0))
        with api_errors("listar modelos"):
            ids = {m.id.removeprefix("models/") for m in client.models.list()}
        faltando = [m for m in (config.vision_model, config.stt_model, config.tts_model)
                    if m not in ids]
        if faltando:
            return f"conectado; modelos não listados p/ sua conta: {', '.join(faltando)}"
        return "conectado; modelos configurados disponíveis"

    checar(f"Conexão com {config.provider.capitalize()} (RF03)", api)

    print("\nDiagnóstico — Visão e Interpretação do Ambiente com LLM\n")
    for nome, ok, detalhe in resultados:
        print(f"  [{OK if ok else FALHA}] {nome:<30} {detalhe}")
    tudo_ok = all(ok for _, ok, _ in resultados)
    print("\nTudo pronto!\n" if tudo_ok else "\nCorrija os itens com FALHA (veja o README).\n")
    return tudo_ok
