"""Folha de estilo (QSS) da aplicação.

Tema: cinza e branco, com poucos detalhes em laranja. O laranja marca só o que pede atenção
(gravando, foco, conversa selecionada, borda da resposta, câmera ao vivo); vermelho e âmbar
ficam reservados para erros e avisos.
"""

# --- paleta -------------------------------------------------------------------
ACCENT = "#f97316"        # laranja: destaques
ACCENT_HOVER = "#ea580c"
ACCENT_SOFT = "#fff4ec"   # fundo laranja bem claro
ACCENT_TEXT = "#c2410c"   # texto laranja legível sobre fundo claro

BG = "#f3f3f4"            # fundo da janela
SURFACE = "#ffffff"       # cartões
SURFACE_2 = "#f7f7f8"     # caixas internas
BORDER = "#e4e4e7"
BORDER_STRONG = "#d4d4d8"
TEXT = "#18181b"
TEXT_2 = "#3f3f46"
MUTED = "#71717a"
SUBTLE = "#a1a1aa"

GRAPHITE = "#1f1f23"      # barra lateral e botão principal
GRAPHITE_2 = "#2b2b30"
GRAPHITE_3 = "#3a3a40"
ON_DARK = "#f4f4f5"
ON_DARK_MUTED = "#a1a1aa"

STYLE = f"""
QWidget {{
    font-family: "Segoe UI", "SF Pro Text", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 14px;
    color: {TEXT};
}}
QMainWindow, #root {{ background: {BG}; }}

#appTitle {{ font-size: 21px; font-weight: 700; color: {TEXT}; }}
#appSubtitle {{ color: {MUTED}; font-size: 13px; }}

#statusPill {{
    border-radius: 14px; padding: 6px 14px; font-weight: 600;
    background: {SURFACE}; color: {TEXT_2}; border: 1px solid {BORDER};
}}
#statusPill[tipo="ocioso"]      {{ background: {SURFACE}; color: {TEXT_2}; border-color: {BORDER}; }}
#statusPill[tipo="ouvindo"]     {{ background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border-color: #fed7aa; }}
#statusPill[tipo="trabalhando"] {{ background: {SURFACE}; color: {TEXT_2}; border-color: {BORDER_STRONG}; }}
#statusPill[tipo="falando"]     {{ background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border-color: #fed7aa; }}
#statusPill[tipo="ok"]          {{ background: {GRAPHITE}; color: {ON_DARK}; border-color: {GRAPHITE}; }}
#statusPill[tipo="erro"]        {{ background: #fef2f2; color: #b91c1c; border-color: #fecaca; }}

#card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px;
}}
#cardTitle {{
    font-size: 11px; font-weight: 700; color: {MUTED};
    letter-spacing: 0.8px; text-transform: uppercase;
}}
#imageView {{
    background: {GRAPHITE}; border-radius: 10px; color: {ON_DARK_MUTED}; font-size: 13px;
}}

#questionText {{
    font-size: 16px; color: {TEXT}; background: {SURFACE_2};
    border: 1px solid {BORDER}; border-radius: 10px; padding: 12px;
}}
#answerText {{
    font-size: 17px; color: {TEXT}; background: {SURFACE};
    border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};
    border-radius: 10px; padding: 14px;
}}
#answerText[vazio="true"], #questionText[vazio="true"] {{
    color: {SUBTLE}; background: {SURFACE_2}; border: 1px dashed {BORDER_STRONG};
}}

#micButton {{
    background: {GRAPHITE}; color: {ON_DARK}; border: none; border-radius: 30px;
    font-size: 17px; font-weight: 700; padding: 14px 28px; min-height: 32px;
}}
#micButton:hover {{ background: {GRAPHITE_3}; }}
#micButton:disabled {{ background: {BORDER_STRONG}; color: {MUTED}; }}
#micButton[modo="ouvindo"] {{ background: {ACCENT}; color: #ffffff; }}
#micButton[modo="ouvindo"]:hover {{ background: {ACCENT_HOVER}; }}
#micButton[modo="falando"] {{ background: {GRAPHITE_2}; color: #ffffff; border: 2px solid {ACCENT}; }}

QPushButton#secondary {{
    background: {SURFACE}; color: {TEXT_2}; border: 1px solid {BORDER_STRONG};
    border-radius: 8px; padding: 7px 14px; font-weight: 600;
}}
QPushButton#secondary:hover {{ background: {SURFACE_2}; border-color: {SUBTLE}; color: {TEXT}; }}
QPushButton#secondary:pressed {{ background: {BORDER}; }}
QPushButton#secondary:disabled {{ color: {SUBTLE}; border-color: {BORDER}; }}

QLineEdit {{
    background: {SURFACE}; border: 1px solid {BORDER_STRONG}; border-radius: 8px;
    padding: 9px 12px; font-size: 14px; selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QProgressBar#level {{
    background: {BORDER}; border: none; border-radius: 4px; max-height: 8px;
}}
QProgressBar#level::chunk {{ background: {ACCENT}; border-radius: 4px; }}

#step {{
    border-radius: 8px; padding: 7px 4px; font-size: 12px; font-weight: 600;
    background: {SURFACE}; color: {SUBTLE}; border: 1px solid {BORDER};
}}
#step[estado="ativo"]  {{ background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border-color: #fdba74; }}
#step[estado="feito"]  {{ background: #ebebed; color: {TEXT_2}; border-color: #ebebed; }}
#step[estado="erro"]   {{ background: #fef2f2; color: #b91c1c; border-color: #fecaca; }}
#step[estado="pulado"] {{ background: {SURFACE_2}; color: {BORDER_STRONG}; border-color: {BORDER}; }}
#stepArrow {{ color: {BORDER_STRONG}; font-size: 16px; }}

#errorBanner {{
    background: #fef2f2; color: #991b1b; border: 1px solid #fecaca;
    border-radius: 10px; padding: 10px 14px;
}}
#warnBanner {{
    background: #fffbeb; color: #92400e; border: 1px solid #fde68a;
    border-radius: 10px; padding: 10px 14px;
}}

QListWidget {{
    border: none; background: transparent; font-size: 13px; outline: none;
}}
QListWidget::item {{ padding: 6px 4px; border-bottom: 1px solid {SURFACE_2}; color: {TEXT_2}; }}
QListWidget::item:hover {{ background: {SURFACE_2}; }}
QListWidget::item:selected {{
    background: {SURFACE_2}; color: {TEXT}; border-left: 2px solid {ACCENT};
}}

#sidebar {{ background: {GRAPHITE}; }}
#sidebarTitle {{ color: {ON_DARK}; font-size: 16px; font-weight: 700; }}
#sidebar QLabel#hint {{ color: {ON_DARK_MUTED}; }}
#sidebar QLineEdit {{
    background: {GRAPHITE_2}; border: 1px solid {GRAPHITE_3}; color: {ON_DARK}; padding: 8px 10px;
}}
#sidebar QLineEdit:focus {{ border-color: {ACCENT}; }}
QPushButton#newChat {{
    background: {SURFACE}; color: {TEXT}; border: none; border-radius: 10px;
    padding: 11px 14px; font-weight: 700; text-align: left;
}}
QPushButton#newChat:hover {{ background: #ebebed; }}
QPushButton#newChat:pressed {{ background: {BORDER_STRONG}; }}
QPushButton#refreshChats {{
    background: {GRAPHITE_2}; color: {ON_DARK_MUTED}; border: 1px solid {GRAPHITE_3};
    border-radius: 8px; font-size: 16px;
    min-width: 30px; max-width: 30px; min-height: 26px; max-height: 26px;
}}
QPushButton#refreshChats:hover {{ background: {GRAPHITE_3}; color: {ACCENT}; }}
#conversationList {{ background: transparent; color: #d4d4d8; outline: none; }}
#conversationList::item {{
    padding: 9px 10px; border-radius: 8px; border-bottom: none; margin: 1px 0;
    border-left: 3px solid transparent; color: #d4d4d8;
}}
#conversationList::item:disabled {{ color: #8b8b94; padding-top: 12px; }}  /* rótulos de dia */
#conversationList::item:hover {{ background: {GRAPHITE_2}; }}
#conversationList::item:selected {{
    background: {GRAPHITE_3}; color: #ffffff; border-left: 3px solid {ACCENT};
}}
QPushButton#danger {{
    background: rgba(239, 68, 68, 0.08); color: #fca5a5;
    border: 1px solid rgba(248, 113, 113, 0.30); border-radius: 10px;
    padding: 10px 14px; font-weight: 600; letter-spacing: 0.2px;
}}
QPushButton#danger:hover {{ background: #dc2626; border-color: #dc2626; color: #ffffff; }}
QPushButton#danger:pressed {{ background: #b91c1c; border-color: #b91c1c; }}
QPushButton#danger:disabled {{
    background: transparent; color: #63636b; border: 1px solid {GRAPHITE_3};
}}

#textScroll, #textScroll > QWidget > QWidget {{ background: transparent; }}
#textScroll QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
#textScroll QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; border-radius: 4px; min-height: 28px; }}
#textScroll QScrollBar::handle:vertical:hover {{ background: {SUBTLE}; }}
#textScroll QScrollBar::add-line:vertical, #textScroll QScrollBar::sub-line:vertical {{ height: 0; }}

QStatusBar {{ background: {SURFACE}; color: {MUTED}; font-size: 12px; border-top: 1px solid {BORDER}; }}
#camBadge {{ font-size: 12px; font-weight: 600; color: {MUTED}; }}
#camBadge[estado="ok"]    {{ color: {ACCENT}; }}
#camBadge[estado="falha"] {{ color: #dc2626; }}
#hint {{ color: {MUTED}; font-size: 12px; }}

#navRail {{ background: #141417; border-right: 1px solid #26262b; }}
#appMark {{
    background: {ACCENT}; color: #ffffff; border-radius: 10px;
    font-size: 15px; font-weight: 800; letter-spacing: 0.5px;
}}
QToolButton#navButton {{
    background: transparent; color: #8b8b94; border: none; border-radius: 10px;
    padding: 8px 2px 6px 2px; font-size: 11px; font-weight: 600;
}}
QToolButton#navButton:hover {{ background: {GRAPHITE_2}; color: {ON_DARK}; }}
QToolButton#navButton:checked {{ background: {GRAPHITE_2}; color: #ffffff; }}

#page, #pageBody {{ background: {BG}; }}
#pageTitle {{ font-size: 24px; font-weight: 700; color: {TEXT}; }}
#pageSubtitle {{ font-size: 14px; color: {MUTED}; }}
#helpText {{ font-size: 14px; color: {TEXT_2}; }}
#stepNumber {{
    background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border: 1px solid #fed7aa;
    border-radius: 14px; font-weight: 700;
}}
#kbd {{
    background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER_STRONG};
    border-bottom: 2px solid {BORDER_STRONG}; border-radius: 6px;
    padding: 4px 10px; font-family: "Consolas", "SF Mono", monospace; font-size: 12px;
    min-width: 110px;
}}

QPushButton#primary {{
    background: {GRAPHITE}; color: #ffffff; border: none; border-radius: 10px;
    padding: 10px 18px; font-weight: 700;
}}
QPushButton#primary:hover {{ background: {GRAPHITE_3}; }}
QPushButton#primary:disabled {{ background: {BORDER_STRONG}; color: {MUTED}; }}

#checkRow {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
#checkName {{ font-size: 15px; font-weight: 700; color: {TEXT}; }}
#checkDetail {{ font-size: 13px; color: {MUTED}; }}
#checkHint {{
    font-size: 13px; color: {TEXT_2}; background: {SURFACE_2};
    border-left: 3px solid {ACCENT}; border-radius: 6px; padding: 8px 10px; margin-top: 4px;
}}
#checkBadge {{
    border-radius: 8px; padding: 5px 0; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;
    background: {SURFACE_2}; color: {SUBTLE}; border: 1px solid {BORDER};
}}
#checkBadge[estado="rodando"] {{ background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border-color: #fed7aa; }}
#checkBadge[estado="ok"]      {{ background: {GRAPHITE}; color: #ffffff; border-color: {GRAPHITE}; }}
#checkBadge[estado="falha"]   {{ background: #fef2f2; color: #b91c1c; border-color: #fecaca; }}
#diagSummary {{
    font-size: 14px; color: {TEXT_2}; background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 12px 16px;
}}
#diagSummary[estado="rodando"] {{ background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border-color: #fed7aa; }}
#diagSummary[estado="ok"]      {{ background: {SURFACE}; color: {TEXT}; border-left: 3px solid {ACCENT}; }}
#diagSummary[estado="falha"]   {{ background: #fef2f2; color: #991b1b; border-color: #fecaca; }}

QComboBox, QDoubleSpinBox {{
    background: {SURFACE}; border: 1px solid {BORDER_STRONG}; border-radius: 8px;
    padding: 8px 12px; min-height: 20px;
}}
QComboBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER}; selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT_TEXT}; outline: none; padding: 4px;
}}
QCheckBox {{ spacing: 10px; color: {TEXT_2}; padding: 4px 0; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px; border: 1px solid {BORDER_STRONG};
    background: {SURFACE};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
#pageBody QLabel {{ color: {TEXT_2}; }}
#pageBody QLabel#pageTitle {{ color: {TEXT}; }}
#pageBody QLabel#hint {{ color: {MUTED}; }}
#settingsStatus {{
    border-radius: 12px; padding: 12px 16px; font-size: 14px;
    background: {SURFACE}; border: 1px solid {BORDER}; border-left: 3px solid {ACCENT}; color: {TEXT};
}}
#settingsStatus[estado="erro"] {{ background: #fef2f2; color: #991b1b; border-color: #fecaca; }}

QToolTip {{
    background: {GRAPHITE}; color: {ON_DARK}; border: 1px solid {GRAPHITE_3};
    border-radius: 6px; padding: 6px 8px;
}}
QMenu {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; color: {TEXT_2}; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; }}
"""
