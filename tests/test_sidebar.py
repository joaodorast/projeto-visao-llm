"""Barra lateral de conversas (PyQt5 offscreen): listar, abrir, continuar, nova, apagar e atualizar."""

from datetime import datetime, timedelta

import cv2
import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import FakeRecorder, FakeSpeaker, FakeSTT, FakeVision  # noqa: E402
from test_gui import esperar  # noqa: E402
from visao_llm.config import Config  # noqa: E402
from visao_llm.gui import sidebar as sidebar_mod  # noqa: E402
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
def jpeg(frame):
    return cv2.imencode(".jpg", frame)[1].tobytes()


def gravar(store, jpeg, sessao, pergunta, resposta, minutos):
    store.save(InteractionResult(
        pergunta=pergunta, resposta=resposta, image_jpeg=jpeg, sessao=sessao,
        timestamp=datetime.now().replace(microsecond=0) - timedelta(minutes=minutos)))


@pytest.fixture
def pasta(tmp_path, jpeg):
    store = HistoryStore(tmp_path)
    gravar(store, jpeg, "A", "O que está na mesa?", "Um notebook.", 30)
    gravar(store, jpeg, "A", "E de que cor é?", "Preto.", 29)
    gravar(store, jpeg, "B", "Quantas pessoas há aqui?", "Nenhuma.", 5)
    return tmp_path


class Fabrica:
    """Cria o Assistant e guarda a visão falsa para inspecionar o contexto enviado."""

    def __init__(self, pasta=None):
        self.vision = FakeVision()
        self.store = HistoryStore(pasta) if pasta is not None else None

    def __call__(self, frames, player):
        return Assistant(frame_provider=frames, recorder=FakeRecorder(), stt=FakeSTT(),
                         vision=self.vision, speaker=FakeSpeaker(), store=self.store)


def janela(pasta, imagem, fabrica=None, salvar=True):
    cfg = Config(api_key="k", camera_source=str(imagem), history_dir=pasta, save_history=salvar)
    w = MainWindow(cfg, fabrica or Fabrica())
    w.show()
    return w


def itens(w):
    lista = w.sidebar.list
    return [lista.item(i) for i in range(lista.count())]


def conversas_na_lista(w):
    return [i.data(Qt.UserRole) for i in itens(w) if i.data(Qt.UserRole) and i.data(Qt.UserRole + 1)]


def clicar(w, sessao):
    item = next(i for i in itens(w) if i.data(Qt.UserRole) == sessao)
    w.sidebar.list.setCurrentItem(item)
    w.sidebar.list.itemClicked.emit(item)


def test_lista_conversas_salvas_com_nova_conversa_no_topo(app, pasta, imagem_teste):
    w = janela(pasta, imagem_teste)
    try:
        textos = [i.text() for i in itens(w)]
        assert textos[0].startswith("Nova conversa")
        assert conversas_na_lista(w) == ["B", "A"]  # a mais recente primeiro
        assert any("2 perguntas" in t for t in textos)
        assert any(t == "HOJE" for t in textos)
    finally:
        w.close()


def test_abrir_conversa_carrega_perguntas_foto_e_resposta(app, pasta, imagem_teste):
    w = janela(pasta, imagem_teste)
    try:
        clicar(w, "A")
        assert w.history.count() == 2
        assert w.question_label.text() == "E de que cor é?"
        assert w.answer_label.text() == "Preto."
        assert w.captured_view.has_image()
        # clicar numa pergunta antiga da conversa mostra a foto salva em disco
        w.history.itemClicked.emit(w.history.item(1))
        assert w.question_label.text() == "O que está na mesa?"
        assert w.captured_view.has_image()
    finally:
        w.close()


def test_continuar_conversa_antiga_envia_o_contexto_e_grava_nela(app, pasta, imagem_teste):
    fabrica = Fabrica(pasta)
    w = janela(pasta, imagem_teste, fabrica)
    try:
        assert esperar(app, w.live_view.has_image)
        clicar(w, "A")
        w._start("E o que mais?")
        assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO")
        assert esperar(app, lambda: w.history.count() == 3)

        enviado = fabrica.vision.chamadas[-1][2]
        assert [t.pergunta for t in enviado] == ["O que está na mesa?", "E de que cor é?"]
        a = next(c for c in HistoryStore(pasta).conversations() if c.id == "A")
        assert [e.pergunta[:6] for e in a.entradas][-1] == "E o qu"  # gravada na conversa A
        assert len(HistoryStore(pasta).conversations()) == 2  # não criou uma conversa nova
    finally:
        w.close()


def test_nova_conversa_limpa_a_tela_mantem_as_antigas_e_zera_o_contexto(app, pasta, imagem_teste):
    fabrica = Fabrica(pasta)
    w = janela(pasta, imagem_teste, fabrica)
    try:
        assert esperar(app, w.live_view.has_image)
        clicar(w, "A")
        w.sidebar.new_button.click()
        assert w.history.count() == 0
        assert w.question_label.text() == "Nenhuma pergunta ainda."
        assert itens(w)[0].text().startswith("Nova conversa")
        assert conversas_na_lista(w) == ["B", "A"]

        w._start("pergunta nova")
        assert esperar(app, lambda: not w.busy and w._estado == "CONCLUIDO")
        assert fabrica.vision.chamadas[-1][2] == ()  # sem contexto da conversa anterior
        assert esperar(app, lambda: len(conversas_na_lista(w)) == 3)
        assert conversas_na_lista(w)[0] not in ("A", "B")
    finally:
        w.close()


def test_apagar_conversa_com_confirmacao(app, pasta, imagem_teste, monkeypatch):
    w = janela(pasta, imagem_teste)
    try:
        monkeypatch.setattr(w, "_confirmar_apagar", lambda n: False)
        clicar(w, "B")
        w.sidebar.delete_button.click()
        assert conversas_na_lista(w) == ["B", "A"]  # recusou: nada muda

        monkeypatch.setattr(w, "_confirmar_apagar", lambda n: True)
        w.sidebar.delete_button.click()
        assert conversas_na_lista(w) == ["A"]
        assert [c.id for c in HistoryStore(pasta).conversations()] == ["A"]
    finally:
        w.close()


def test_apagar_a_conversa_aberta_comeca_uma_nova(app, pasta, imagem_teste, monkeypatch):
    w = janela(pasta, imagem_teste)
    try:
        monkeypatch.setattr(w, "_confirmar_apagar", lambda n: True)
        clicar(w, "A")
        w.sidebar.delete_button.click()
        assert w.history.count() == 0 and w._conversa_id != "A"
        assert conversas_na_lista(w) == ["B"]
    finally:
        w.close()


def test_botao_apagar_so_vale_para_conversa_salva(app, pasta, imagem_teste):
    w = janela(pasta, imagem_teste)
    try:
        assert not w.sidebar.delete_button.isEnabled()  # "Nova conversa" não tem o que apagar
        clicar(w, "A")
        assert w.sidebar.delete_button.isEnabled()
    finally:
        w.close()


def test_atualizar_traz_conversas_e_perguntas_novas_do_disco(app, pasta, jpeg, imagem_teste):
    w = janela(pasta, imagem_teste)
    try:
        clicar(w, "A")
        # outra janela do app grava uma conversa nova e mais uma pergunta na conversa aberta
        outro = HistoryStore(pasta)
        gravar(outro, jpeg, "C", "Pergunta feita em outra janela", "ok", 0)
        gravar(outro, jpeg, "A", "Mais uma na conversa A", "sim", 1)
        assert "C" not in conversas_na_lista(w) and w.history.count() == 2

        w.sidebar.refresh_button.click()

        assert "C" in conversas_na_lista(w)
        assert w.history.count() == 3
        assert w.question_label.text() == "Mais uma na conversa A"
    finally:
        w.close()


def test_botao_atualizar_anima_e_volta_ao_normal(app, pasta, imagem_teste):
    w = janela(pasta, imagem_teste)
    try:
        b = w.sidebar.refresh_button
        b.click()
        assert not b.isEnabled() and b.text() in sidebar_mod.QUADROS  # girando
        assert esperar(app, lambda: b.isEnabled(), timeout=3)
        assert b.text() == sidebar_mod.PARADO
        assert sidebar_mod.QUADROS_TOTAIS * sidebar_mod.INTERVALO_MS < 1000  # "bem rapidinha"
    finally:
        w.close()


def test_busca_na_barra_lateral_filtra_por_pergunta_e_resposta(app, pasta, imagem_teste):
    w = janela(pasta, imagem_teste)
    try:
        w.sidebar.search.setText("notebook")  # só na resposta da conversa A
        assert conversas_na_lista(w) == ["A"]
        w.sidebar.search.setText("zzz")
        assert conversas_na_lista(w) == []
        w.sidebar.search.setText("")
        assert conversas_na_lista(w) == ["B", "A"]
    finally:
        w.close()


def test_aviso_quando_a_gravacao_esta_desativada(app, tmp_path, imagem_teste):
    w = janela(tmp_path, imagem_teste, salvar=False)
    try:
        assert "desativada" in w.sidebar.hint.text()
    finally:
        w.close()
