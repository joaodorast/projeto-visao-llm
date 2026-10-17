"""RNF01 — chave fora do código; leitura de configuração."""

import pytest

from visao_llm.config import Config, load_config, parse_camera_source
from visao_llm.errors import ConfigError


def test_ct01_sem_chave_gera_erro_amigavel():
    """CT01: sem OPENAI_API_KEY o app não quebra; gera ConfigError com instrução."""
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        Config(api_key=None).require_api_key()
    with pytest.raises(ConfigError):
        Config(api_key="   ").require_api_key()


def test_ct02_chave_lida_do_ambiente(monkeypatch, tmp_path):
    """CT02: chave e parâmetros vêm do ambiente/.env (RNF01)."""
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-teste\nCAMERA=2\nMODELO_VISAO=modelo-x\nSALVAR_HISTORICO=nao\n")
    for var in ("OPENAI_API_KEY", "CAMERA", "MODELO_VISAO", "SALVAR_HISTORICO"):
        monkeypatch.delenv(var, raising=False)
    cfg = load_config(env)
    assert cfg.require_api_key() == "sk-teste"
    assert cfg.camera_source == 2
    assert cfg.vision_model == "modelo-x"
    assert cfg.save_history is False
    assert "sk-teste" not in repr(cfg)  # a chave nunca aparece em logs/repr


def test_valor_numerico_invalido(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("TIMEOUT_REQUISICAO=abc\n")
    monkeypatch.delenv("TIMEOUT_REQUISICAO", raising=False)
    with pytest.raises(ConfigError, match="TIMEOUT_REQUISICAO"):
        load_config(env)


@pytest.mark.parametrize("entrada,esperado", [
    ("0", 0), ("1", 1), ("", 0), (None, 0), (3, 3),
    ("video.mp4", "video.mp4"), ("rtsp://cam/1", "rtsp://cam/1"),
])
def test_parse_camera_source(entrada, esperado):
    assert parse_camera_source(entrada) == esperado


def test_nenhuma_chave_no_codigo_fonte():
    """RNF01: varre o código-fonte procurando chaves da OpenAI embutidas."""
    import re
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent / "visao_llm"
    padrao = re.compile(r"sk-[A-Za-z0-9_\-]{20,}")
    for arq in raiz.rglob("*.py"):
        assert not padrao.search(arq.read_text(encoding="utf-8")), f"possível chave em {arq}"
