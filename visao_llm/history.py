"""Registro das interações em disco: imagem usada + pergunta + resposta.

Serve como evidência da demonstração (entregável 7) e para depuração.
Estrutura: registros/AAAA-MM-DD/HHMMSS_xxx.jpg  +  registros/interacoes.jsonl
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import InteractionResult

log = logging.getLogger(__name__)


class HistoryStore:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

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
            with (self.pasta / "interacoes.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            return img
        except Exception as exc:  # disco cheio, permissão etc.
            log.warning("Não foi possível salvar o histórico: %s", exc)
            return None
