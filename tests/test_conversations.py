"""Conversas salvas: agrupamento por sessão, registros antigos, exclusão e contexto do assistente."""

import json
from datetime import datetime, timedelta

from conftest import FakeVision
from visao_llm.history import HistoryStore
from visao_llm.models import InteractionResult
from visao_llm.openai_service import Turn
from visao_llm.pipeline import Assistant

AGORA = datetime(2026, 10, 17, 12, 0, 0)


def salvar(store, sessao, pergunta, minutos, resposta="r"):
    return store.save(InteractionResult(
        pergunta=pergunta, resposta=resposta, image_jpeg=b"\xff\xd8x", sessao=sessao,
        timestamp=AGORA + timedelta(minutes=minutos)))


def test_grava_o_id_da_conversa(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "s1", "oi", 0)
    registro = json.loads((tmp_path / "interacoes.jsonl").read_text(encoding="utf-8"))
    assert registro["sessao"] == "s1"


def test_agrupa_por_conversa_e_ordena_pela_atividade_mais_recente(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "A", "a1", 0)
    salvar(store, "B", "b1", 5)
    salvar(store, "A", "a2", 10)  # A teve a atividade mais recente

    conversas = store.conversations()

    assert [c.id for c in conversas] == ["A", "B"]
    assert [e.pergunta for e in conversas[0].entradas] == ["a1", "a2"]  # cronológico
    assert conversas[0].titulo == "a1"
    assert conversas[0].atualizada == AGORA + timedelta(minutes=10)


def test_titulo_longo_e_resumido(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "A", "palavra " * 20, 0)
    titulo = store.conversations()[0].titulo
    assert len(titulo) <= 48 and titulo.endswith("…")


def test_registros_antigos_sem_sessao_viram_uma_conversa_por_dia(tmp_path):
    antigo = {"data_hora": "2026-10-16T09:00:00", "pergunta": "velha", "resposta": "r"}
    (tmp_path / "interacoes.jsonl").write_text(json.dumps(antigo) + "\n", encoding="utf-8")
    store = HistoryStore(tmp_path)
    salvar(store, "nova", "recente", 0)

    ids = [c.id for c in store.conversations()]

    assert ids == ["nova", "dia-2026-10-16"]


def test_apagar_conversa_remove_registros_e_fotos_e_preserva_as_outras(tmp_path):
    store = HistoryStore(tmp_path)
    foto_a = salvar(store, "A", "a1", 0)
    salvar(store, "A", "a2", 1)
    foto_b = salvar(store, "B", "b1", 2)

    assert store.delete_conversation("A") == 2

    assert [c.id for c in store.conversations()] == ["B"]
    assert not foto_a.exists() and foto_b.exists()
    assert not (tmp_path / "interacoes.tmp").exists()


def test_apagar_conversa_inexistente_nao_altera_nada(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "A", "a1", 0)
    antes = (tmp_path / "interacoes.jsonl").read_text(encoding="utf-8")

    assert store.delete_conversation("zzz") == 0
    assert HistoryStore(tmp_path / "vazio").delete_conversation("A") == 0
    assert (tmp_path / "interacoes.jsonl").read_text(encoding="utf-8") == antes


def test_apagar_preserva_linhas_ilegiveis(tmp_path):
    store = HistoryStore(tmp_path)
    salvar(store, "A", "a1", 0)
    with (tmp_path / "interacoes.jsonl").open("a", encoding="utf-8") as f:
        f.write("lixo que não é json\n")

    store.delete_conversation("A")

    assert (tmp_path / "interacoes.jsonl").read_text(encoding="utf-8") == "lixo que não é json\n"


def test_apagar_remove_a_pasta_do_dia_quando_fica_vazia(tmp_path):
    store = HistoryStore(tmp_path)
    foto = salvar(store, "A", "a1", 0)
    store.delete_conversation("A")
    assert not foto.parent.exists()


# ------------------------------------------------------- contexto do assistente
def assistente(frame):
    return Assistant(frame_provider=lambda: frame, recorder=None, stt=None, vision=FakeVision())


def test_assistente_grava_a_sessao_nos_resultados(frame):
    a = assistente(frame)
    assert a.ask_by_text("oi", speak=False).sessao == a.session_id


def test_nova_sessao_zera_o_contexto_e_troca_o_id(frame):
    a = assistente(frame)
    a.ask_by_text("oi", speak=False)
    antigo = a.session_id

    novo = a.new_session()

    assert novo != antigo and a.session_id == novo and not a.historico


def test_retomar_conversa_restaura_so_as_ultimas_trocas(frame):
    a = assistente(frame)
    turnos = [Turn(f"p{i}", f"r{i}") for i in range(6)]

    a.load_session("antiga", turnos)
    a.ask_by_text("nova pergunta", speak=False)

    assert a.session_id == "antiga"
    enviado = a.vision.chamadas[-1][2]
    assert [t.pergunta for t in enviado] == ["p3", "p4", "p5"]  # contexto_turns = 3
