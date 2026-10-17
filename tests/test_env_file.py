"""Atualização do .env pela página Ajustes: só as chaves pedidas, preservando o resto."""

from dotenv import dotenv_values

from visao_llm.env_file import update_env

ORIGINAL = """# Copie este arquivo para ".env" e preencha.
PROVEDOR=gemini
GEMINI_API_KEY=chave-secreta
OPENAI_API_KEY=

# --- Modelos (opcional) ---
#MODELO_VISAO=
CAMERA=0
TTS_ATIVO=true
"""


def test_altera_so_as_chaves_pedidas_e_preserva_comentarios(tmp_path):
    env = tmp_path / ".env"
    env.write_text(ORIGINAL, encoding="utf-8")

    update_env(env, {"CAMERA": "1", "TTS_ATIVO": "false"})

    texto = env.read_text(encoding="utf-8")
    assert texto == ORIGINAL.replace("CAMERA=0", "CAMERA=1").replace("TTS_ATIVO=true", "TTS_ATIVO=false")
    assert "GEMINI_API_KEY=chave-secreta" in texto


def test_ativa_chave_comentada_no_mesmo_lugar(tmp_path):
    env = tmp_path / ".env"
    env.write_text(ORIGINAL, encoding="utf-8")
    update_env(env, {"MODELO_VISAO": "modelo-x"})
    linhas = env.read_text(encoding="utf-8").splitlines()
    assert "MODELO_VISAO=modelo-x" in linhas and "#MODELO_VISAO=" not in linhas
    assert linhas.index("MODELO_VISAO=modelo-x") < linhas.index("CAMERA=0")


def test_chave_nova_vai_para_o_fim(tmp_path):
    env = tmp_path / ".env"
    env.write_text(ORIGINAL, encoding="utf-8")
    update_env(env, {"SILENCIO_SEG": "2"})
    assert env.read_text(encoding="utf-8").rstrip().endswith("SILENCIO_SEG=2")


def test_cria_o_arquivo_se_nao_existir(tmp_path):
    env = tmp_path / "novo.env"
    update_env(env, {"PROVEDOR": "openai"})
    assert dotenv_values(env) == {"PROVEDOR": "openai"}


def test_valores_com_espaco_ficam_entre_aspas_e_sao_lidos_de_volta(tmp_path):
    env = tmp_path / ".env"
    caminho = "C:\\Meus Vídeos\\teste #1.mp4"
    update_env(env, {"CAMERA": caminho, "MODELO_VISAO": ""})
    valores = dotenv_values(env)
    assert valores["CAMERA"] == caminho
    assert valores["MODELO_VISAO"] == ""


def test_nao_deixa_arquivo_temporario(tmp_path):
    env = tmp_path / ".env"
    env.write_text(ORIGINAL, encoding="utf-8")
    update_env(env, {"CAMERA": "2"})
    assert sorted(p.name for p in tmp_path.iterdir()) == [".env"]
