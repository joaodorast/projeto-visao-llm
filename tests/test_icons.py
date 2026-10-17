"""Ícones vetoriais da barra lateral: desenhados, com estados e aplicados aos botões."""

import pytest

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtCore import QSize  # noqa: E402
from PyQt5.QtGui import QIcon  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from visao_llm.gui.icons import plus_icon, search_icon, trash_icon  # noqa: E402
from visao_llm.gui.sidebar import ConversationSidebar  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def cor_mais_forte(icone: QIcon, modo) -> tuple[int, int, int]:
    """Cor do pixel mais opaco do ícone naquele estado."""
    img = icone.pixmap(QSize(20, 20), modo).toImage()
    melhor, cor = -1, (0, 0, 0)
    for x in range(img.width()):
        for y in range(img.height()):
            c = img.pixelColor(x, y)
            if c.alpha() > melhor:
                melhor, cor = c.alpha(), (c.red(), c.green(), c.blue())
    assert melhor > 200, "ícone vazio"
    return cor


@pytest.mark.parametrize("fabrica", [trash_icon, plus_icon, search_icon])
def test_icones_sao_desenhados(app, fabrica):
    icone = fabrica()
    assert not icone.isNull()
    cor_mais_forte(icone, QIcon.Normal)


def test_lixeira_muda_de_cor_por_estado(app):
    icone = trash_icon()
    normal = cor_mais_forte(icone, QIcon.Normal)
    ativo = cor_mais_forte(icone, QIcon.Active)
    desativado = cor_mais_forte(icone, QIcon.Disabled)
    assert ativo == (255, 255, 255)           # branco ao passar o mouse
    assert normal[0] > normal[2]              # tom avermelhado
    assert len({normal, ativo, desativado}) == 3


def test_botoes_da_barra_usam_icones_e_nao_emojis(app):
    s = ConversationSidebar()
    for botao in (s.delete_button, s.new_button):
        assert not botao.icon().isNull()
        assert all(ord(ch) < 0x2000 for ch in botao.text()), botao.text()
    assert s.delete_button.text().strip() == "Apagar conversa"
    assert s.new_button.text().strip() == "Nova conversa"
