"""Tela de histórico (PyQt5, plataforma offscreen): lista, busca, detalhe e botão na janela."""

from datetime import date, datetime, timedelta

import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui.history_dialog import HistoryDialog, resumo, rotulo_dia  # noqa: E402
from visao_llm.gui.main_window import MainWindow  # noqa: E402
from visao_llm.gui.style import STYLE  # noqa: E402
from visao_llm.history import HistoryStore  # noqa: E402
from visao_llm.models import InteractionResult  # noqa: E402
from visao_llm.pipeline import Assistant  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(STYLE)
    return a


@pytest.fixture
def store(tmp_path, frame):
    import cv2
    jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
    s = HistoryStore(tmp_path)
    agora = datetime.now().replace(microsecond=0)
    for pergunta, resposta, quando in [
        ("O que está sobre a mesa?", "Vejo um notebook e uma garrafa.", agora - timedelta(days=2)),
        ("Que cor é a garrafa?", "A garrafa é azul.", agora - timedelta(days=1)),
        ("Quantas pessoas há aqui?", "Não vejo ninguém na imagem.", agora),
    ]:
        s.save(InteractionResult(pergunta=pergunta, resposta=resposta, image_jpeg=jpeg,
                                 timestamp=quando))
    return s


def entradas_visiveis(dialog):
    itens = (dialog.list.item(i) for i in range(dialog.list.count()))
    return [i.data(Qt.UserRole) for i in itens if i.data(Qt.UserRole) is not None]


def test_lista_conversas_agrupadas_por_dia_da_mais_recente(app, store):
    d = HistoryDialog(store)
    assert [e.pergunta for e in entradas_visiveis(d)] == [
        "Quantas pessoas há aqui?", "Que cor é a garrafa?", "O que está sobre a mesa?"]
    cabecalhos = [d.list.item(i).text() for i in range(d.list.count())
                  if d.list.item(i).data(Qt.UserRole) is None]
    assert cabecalhos[:2] == ["HOJE", "ONTEM"] and len(cabecalhos) == 3
    assert d.count_label.text() == "3"


def test_seleciona_a_mais_recente_e_mostra_detalhes(app, store):
    d = HistoryDialog(store)
    assert d.question_label.text() == "Quantas pessoas há aqui?"
    assert d.answer_label.text() == "Não vejo ninguém na imagem."
    assert d.image_view.has_image()


def test_clicar_em_outra_conversa_atualiza_o_painel(app, store):
    d = HistoryDialog(store)
    item = next(d.list.item(i) for i in range(d.list.count())
                if (e := d.list.item(i).data(Qt.UserRole)) and e.pergunta.startswith("Que cor"))
    d.list.setCurrentItem(item)
    assert d.question_label.text() == "Que cor é a garrafa?"
    assert d.answer_label.text() == "A garrafa é azul."


def test_busca_filtra_por_pergunta_e_resposta(app, store):
    d = HistoryDialog(store)
    d.search.setText("notebook")  # só aparece na resposta
    assert [e.pergunta for e in entradas_visiveis(d)] == ["O que está sobre a mesa?"]
    assert d.count_label.text() == "1 de 3"
    d.search.setText("zzz")
    assert entradas_visiveis(d) == []
    assert d.question_label.text() == "Nenhum resultado para a busca."
    d.search.setText("")
    assert len(entradas_visiveis(d)) == 3


def test_sem_historico_mostra_mensagem_vazia(app, tmp_path):
    d = HistoryDialog(HistoryStore(tmp_path))
    assert d.question_label.text() == "Nenhuma conversa salva ainda."
    assert not d.image_view.has_image()


def test_imagem_apagada_nao_quebra_a_tela(app, store):
    for jpg in store.pasta.rglob("*.jpg"):
        jpg.unlink()
    d = HistoryDialog(store)
    assert len(entradas_visiveis(d)) == 3
    assert not d.image_view.has_image()
    assert "Imagem não encontrada" in d.image_view.text()


def test_reload_pega_conversas_novas(app, store, frame):
    d = HistoryDialog(store)
    store.save(InteractionResult(pergunta="nova", resposta="r", image_jpeg=b"x",
                                 timestamp=datetime.now() + timedelta(minutes=1)))
    d.reload()
    assert entradas_visiveis(d)[0].pergunta == "nova"


def test_botao_historico_da_janela_abre_a_tela(app, tmp_path, store):
    def fabrica(frames, player):
        return Assistant(frame_provider=frames, recorder=FakeRecorder(), stt=FakeSTT(),
                         vision=FakeVision(), speaker=FakeSpeaker())

    cfg = Config(api_key="k", camera_source="inexistente.jpg", history_dir=store.pasta)
    w = MainWindow(cfg, fabrica, start_camera=False)
    try:
        w.history_button.click()
        assert w._history_dialog is not None and w._history_dialog.isVisible()
        assert len(entradas_visiveis(w._history_dialog)) == 3
        primeiro = w._history_dialog
        w.history_button.click()  # reaproveita a mesma janela
        assert w._history_dialog is primeiro
    finally:
        w._history_dialog and w._history_dialog.close()
        w.close()


def test_rotulos_auxiliares():
    hoje = date(2026, 10, 17)
    assert rotulo_dia(hoje, hoje) == "Hoje"
    assert rotulo_dia(hoje - timedelta(days=1), hoje) == "Ontem"
    assert rotulo_dia(date(2026, 10, 1), hoje) == "01/10/2026"
    assert resumo("  texto   curto ") == "texto curto"
    assert resumo("a" * 100, 10) == "a" * 9 + "…"
