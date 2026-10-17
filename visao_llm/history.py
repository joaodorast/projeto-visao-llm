"""Registro das interações em disco: imagem usada + pergunta + resposta.

Serve como evidência da demonstração (entregável 7) e para depuração.
Estrutura: registros/AAAA-MM-DD/HHMMSS_xxx.jpg  +  registros/interacoes.jsonl

`HistoryStore.load()` lê esse arquivo de volta para a tela de histórico.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import InteractionResult

log = logging.getLogger(__name__)


ARQUIVO = "interacoes.jsonl"


@dataclass
class HistoryEntry:
    """Uma interação já gravada em disco."""

    data_hora: datetime
    origem: str
    pergunta: str
    resposta: str
    imagem: Path | None  # None se o arquivo foi apagado ou movido
    tempos: dict[str, float] = field(default_factory=dict)


class HistoryStore:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    def load(self, limite: int | None = None) -> list[HistoryEntry]:
        """Lê as interações salvas, da mais recente para a mais antiga.

        Linhas corrompidas são ignoradas; nunca lança exceção por causa do arquivo.
        """
        arquivo = self.pasta / ARQUIVO
        if not arquivo.is_file():
            return []
        entradas: list[HistoryEntry] = []
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            log.warning("Não foi possível ler o histórico: %s", exc)
            return []
        for linha in linhas:
            if not linha.strip():
                continue
            try:
                r = json.loads(linha)
                # o caminho é gravado com "\\" no Windows; normaliza para abrir em qualquer SO
                caminho = self.pasta / str(r.get("imagem", "")).replace("\\", "/")
                entradas.append(HistoryEntry(
                    data_hora=datetime.fromisoformat(r["data_hora"]),
                    origem=r.get("origem", "voz"),
                    pergunta=r["pergunta"],
                    resposta=r["resposta"],
                    imagem=caminho if r.get("imagem") and caminho.is_file() else None,
                    tempos=r.get("tempos_s") or {},
                ))
            except (ValueError, KeyError, TypeError):
                log.warning("Linha inválida ignorada em %s", arquivo.name)
        entradas.sort(key=lambda e: e.data_hora, reverse=True)
        return entradas[:limite] if limite else entradas

    def save(self, resultado: InteractionResult) -> Path | None:
        """Salva a interação. Falhas aqui nunca interrompem o app (retorna None)."""
        try:
            ts = resultado.timestamp
            dia = self.pasta / ts.strftime("%Y-%m-%d")
            dia.mkdir(parents=True, exist_ok=True)
            img = dia / f"{ts.strftime('%H%M%S_%f')[:-3]}.jpg"
            img.write_bytes(resultado.image_jpeg)
            registro = {
                "data_hora": ts.isoformat(timespec="seconds"),
                "origem": resultado.origem,
                "pergunta": resultado.pergunta,
                "resposta": resultado.resposta,
                "imagem": str(img.relative_to(self.pasta)),
                "tempos_s": {k: round(v, 2) for k, v in resultado.tempos.items()},
                "aviso_voz": resultado.aviso_voz,
            }
            with (self.pasta / ARQUIVO).open("a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            return img
        except Exception as exc:  # disco cheio, permissão etc.
            log.warning("Não foi possível salvar o histórico: %s", exc)
            return None
