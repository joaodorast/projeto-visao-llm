"""Registro das conversas em disco: imagem usada + pergunta + resposta de cada interação.

Serve como evidência da demonstração (entregável 7), alimenta a barra lateral de conversas e
permite retomar uma conversa antiga.
Estrutura: registros/AAAA-MM-DD/HHMMSS_xxx.jpg  +  registros/interacoes.jsonl

Cada linha do .jsonl é uma interação e leva o campo "sessao" (id da conversa). Registros
antigos, sem esse campo, são agrupados em uma conversa por dia ("dia-AAAA-MM-DD").
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import InteractionResult

log = logging.getLogger(__name__)


ARQUIVO = "interacoes.jsonl"
TITULO_MAX = 48


@dataclass
class HistoryEntry:
    """Uma interação já gravada em disco."""

    data_hora: datetime
    origem: str
    pergunta: str
    resposta: str
    imagem: Path | None  # None se o arquivo foi apagado ou movido
    tempos: dict[str, float] = field(default_factory=dict)
    sessao: str = ""


@dataclass
class Conversation:
    """Interações de uma mesma sessão, da mais antiga para a mais recente."""

    id: str
    entradas: list[HistoryEntry]

    @property
    def titulo(self) -> str:
        """A primeira pergunta, resumida (como o título de um chat de IA)."""
        texto = " ".join(self.entradas[0].pergunta.split())
        return texto if len(texto) <= TITULO_MAX else texto[:TITULO_MAX - 1].rstrip() + "…"

    @property
    def atualizada(self) -> datetime:
        return self.entradas[-1].data_hora


def _sessao_de(registro: dict, data_hora: datetime) -> str:
    return registro.get("sessao") or f"dia-{data_hora:%Y-%m-%d}"


class HistoryStore:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    @property
    def arquivo(self) -> Path:
        return self.pasta / ARQUIVO

    def _caminho_imagem(self, registro: dict) -> Path | None:
        if not registro.get("imagem"):
            return None
        # o caminho é gravado com "\\" no Windows; normaliza para abrir em qualquer SO
        return self.pasta / str(registro["imagem"]).replace("\\", "/")

    def _ler_registros(self) -> list[tuple[str, dict]]:
        """(linha original, registro) das linhas válidas; ignora as corrompidas."""
        if not self.arquivo.is_file():
            return []
        try:
            linhas = self.arquivo.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            log.warning("Não foi possível ler o histórico: %s", exc)
            return []
        validos = []
        for linha in linhas:
            if not linha.strip():
                continue
            try:
                registro = json.loads(linha)
                datetime.fromisoformat(registro["data_hora"])
                registro["pergunta"], registro["resposta"]  # noqa: B018 - exige os campos
            except (ValueError, KeyError, TypeError):
                log.warning("Linha inválida ignorada em %s", ARQUIVO)
                continue
            validos.append((linha, registro))
        return validos

    def load(self, limite: int | None = None) -> list[HistoryEntry]:
        """Lê as interações salvas, da mais recente para a mais antiga.

        Linhas corrompidas são ignoradas; nunca lança exceção por causa do arquivo.
        """
        entradas = []
        for _, r in self._ler_registros():
            data_hora = datetime.fromisoformat(r["data_hora"])
            caminho = self._caminho_imagem(r)
            entradas.append(HistoryEntry(
                data_hora=data_hora,
                origem=r.get("origem", "voz"),
                pergunta=r["pergunta"],
                resposta=r["resposta"],
                imagem=caminho if caminho is not None and caminho.is_file() else None,
                tempos=r.get("tempos_s") or {},
                sessao=_sessao_de(r, data_hora),
            ))
        entradas.sort(key=lambda e: e.data_hora, reverse=True)
        return entradas[:limite] if limite else entradas

    def conversations(self) -> list[Conversation]:
        """Conversas salvas, da que teve atividade mais recente para a mais antiga."""
        grupos: dict[str, list[HistoryEntry]] = {}
        for entrada in reversed(self.load()):  # cronológico
            grupos.setdefault(entrada.sessao, []).append(entrada)
        conversas = [Conversation(sid, itens) for sid, itens in grupos.items()]
        conversas.sort(key=lambda c: c.atualizada, reverse=True)
        return conversas

    def save(self, resultado: InteractionResult) -> Path | None:
        """Salva a interação. Falhas aqui nunca interrompem o app (retorna None)."""
        try:
            ts = resultado.timestamp
            img = None
            if resultado.image_jpeg:  # sem foto quando a câmera estava desligada
                dia = self.pasta / ts.strftime("%Y-%m-%d")
                dia.mkdir(parents=True, exist_ok=True)
                img = dia / f"{ts.strftime('%H%M%S_%f')[:-3]}.jpg"
                img.write_bytes(resultado.image_jpeg)
            registro = {
                "sessao": resultado.sessao,
                "data_hora": ts.isoformat(timespec="seconds"),
                "origem": resultado.origem,
                "pergunta": resultado.pergunta,
                "resposta": resultado.resposta,
                "imagem": str(img.relative_to(self.pasta)) if img else None,
                "tempos_s": {k: round(v, 2) for k, v in resultado.tempos.items()},
                "aviso_voz": resultado.aviso_voz,
            }
            with self.arquivo.open("a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            return img
        except Exception as exc:  # disco cheio, permissão etc.
            log.warning("Não foi possível salvar o histórico: %s", exc)
            return None

    def delete_conversation(self, session_id: str) -> int:
        """Apaga uma conversa inteira (registros e fotos). Retorna quantas interações removeu.

        O arquivo é reescrito em um temporário e trocado de uma vez, para nunca ficar pela
        metade. Linhas corrompidas que já existiam são preservadas.
        """
        if not self.arquivo.is_file():
            return 0
        try:
            linhas = self.arquivo.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            log.warning("Não foi possível ler o histórico: %s", exc)
            return 0
        manter, imagens, removidas = [], [], 0
        for linha in linhas:
            try:
                r = json.loads(linha)
                if _sessao_de(r, datetime.fromisoformat(r["data_hora"])) == session_id:
                    removidas += 1
                    caminho = self._caminho_imagem(r)
                    if caminho is not None:
                        imagens.append(caminho)
                    continue
            except (ValueError, KeyError, TypeError):
                pass  # linha ilegível: não é possível saber a quem pertence, então fica
            if linha.strip():
                manter.append(linha)
        if not removidas:
            return 0
        temporario = self.arquivo.with_suffix(".tmp")
        try:
            temporario.write_text("".join(f"{linha}\n" for linha in manter), encoding="utf-8")
            os.replace(temporario, self.arquivo)
        except OSError as exc:
            log.warning("Não foi possível apagar a conversa: %s", exc)
            temporario.unlink(missing_ok=True)
            return 0
        for caminho in imagens:
            try:
                caminho.unlink(missing_ok=True)
                if caminho.parent != self.pasta and not any(caminho.parent.iterdir()):
                    caminho.parent.rmdir()
            except OSError as exc:  # a conversa já saiu do histórico; foto órfã não é grave
                log.warning("Não foi possível apagar %s: %s", caminho, exc)
        return removidas
