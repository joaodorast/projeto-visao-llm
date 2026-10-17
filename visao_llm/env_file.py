"""Atualização segura do arquivo .env (usada pela página Ajustes).

Altera só as chaves pedidas e preserva comentários, ordem e as demais linhas. Uma chave que só
existe comentada (ex.: `#MODELO_VISAO=` do .env.example) é ativada no mesmo lugar; chaves novas vão
para o fim. O arquivo é gravado em um temporário e trocado de uma vez, para nunca ficar pela metade.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


def _formatar(valor: str) -> str:
    """Coloca aspas quando o valor tem espaço, '#' ou aspas (ex.: caminho de vídeo com espaços)."""
    if valor == "" or not re.search(r"[\s#'\"]", valor):
        return valor
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def update_env(caminho: str | os.PathLike, valores: dict[str, str]) -> None:
    caminho = Path(caminho)
    linhas = caminho.read_text(encoding="utf-8").splitlines() if caminho.is_file() else []
    pendentes = dict(valores)

    def substituir(padrao: str) -> None:
        for i, linha in enumerate(linhas):
            m = re.match(padrao, linha)
            if m and m.group(1) in pendentes:
                chave = m.group(1)
                linhas[i] = f"{chave}={_formatar(pendentes.pop(chave))}"

    substituir(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")  # chaves ativas
    substituir(r"^\s*#\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")            # chaves só comentadas
    if pendentes:
        if linhas and linhas[-1].strip():
            linhas.append("")
        linhas.extend(f"{chave}={_formatar(valor)}" for chave, valor in pendentes.items())

    temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        temporario.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        os.replace(temporario, caminho)
    finally:
        temporario.unlink(missing_ok=True)
