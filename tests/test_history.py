"""Histórico em disco: gravação, releitura (tela de histórico) e tolerância a arquivos ruins."""

import json
from datetime import datetime

from visao_llm.history import HistoryStore
from visao_llm.models import InteractionResult


def salvar(store, pergunta, resposta, quando, jpeg=b"\xff\xd8fake"):
    return store.save(InteractionResult(pergunta=pergunta, resposta=resposta, image_jpeg=jpeg,
                                        timestamp=quando, tempos={"llm": 1.234}))


def test_load_sem_arquivo_devolve_lista_vazia(tmp_path):
    assert HistoryStore(tmp_path / "nao_existe").load() == []


def test_load_devolve_da_mais_recente_para_a_mais_antiga(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "primeira", "r1", datetime(2026, 10, 16, 9, 0, 0))
    salvar(store, "terceira", "r3", datetime(2026, 10, 17, 9, 0, 0))
    salvar(store, "segunda", "r2", datetime(2026, 10, 16, 18, 30, 0))

    entradas = store.load()

    assert [e.pergunta for e in entradas] == ["terceira", "segunda", "primeira"]
    assert entradas[0].resposta == "r3" and entradas[0].origem == "voz"
    assert entradas[0].tempos == {"llm": 1.23}
    assert entradas[0].imagem is not None and entradas[0].imagem.is_file()


def test_load_respeita_o_limite(tmp_path):
    store = HistoryStore(tmp_path)
    for i in range(5):
        salvar(store, f"p{i}", "r", datetime(2026, 10, 17, 9, 0, i))
    assert [e.pergunta for e in store.load(limite=2)] == ["p4", "p3"]


def test_load_ignora_linhas_corrompidas(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "boa", "r", datetime(2026, 10, 17, 9, 0, 0))
    with (tmp_path / "interacoes.jsonl").open("a", encoding="utf-8") as f:
        f.write("isto não é json\n")
        f.write(json.dumps({"data_hora": "ontem", "pergunta": "x", "resposta": "y"}) + "\n")
        f.write(json.dumps({"pergunta": "sem data"}) + "\n\n")

    assert [e.pergunta for e in store.load()] == ["boa"]


def test_load_com_imagem_apagada_mantem_a_conversa(tmp_path):
    store = HistoryStore(tmp_path)
    img = salvar(store, "p", "r", datetime(2026, 10, 17, 9, 0, 0))
    img.unlink()

    entrada, = store.load()
    assert entrada.imagem is None and entrada.pergunta == "p"


def test_load_aceita_caminho_com_barra_invertida_do_windows(tmp_path):
    """O jsonl gravado no Windows usa '\\' no caminho da imagem; deve abrir em qualquer SO."""
    store = HistoryStore(tmp_path)
    img = salvar(store, "p", "r", datetime(2026, 10, 17, 9, 0, 0))
    registro = json.loads((tmp_path / "interacoes.jsonl").read_text(encoding="utf-8"))
    registro["imagem"] = str(img.relative_to(tmp_path)).replace("/", "\\")
    (tmp_path / "interacoes.jsonl").write_text(json.dumps(registro) + "\n", encoding="utf-8")

    assert store.load()[0].imagem == img
