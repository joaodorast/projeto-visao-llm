"""Folha de estilo (QSS) da aplicação."""

ACCENT = "#2563eb"

STYLE = f"""
QWidget {{
    font-family: "Segoe UI", "SF Pro Text", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 14px;
    color: #1e293b;
}}
QMainWindow, #root {{ background: #eef2f8; }}

#appTitle {{ font-size: 21px; font-weight: 700; color: #0f2747; }}
#appSubtitle {{ color: #64748b; font-size: 13px; }}

#statusPill {{
    border-radius: 14px; padding: 6px 14px; font-weight: 600;
    background: #e2e8f0; color: #334155;
}}
#statusPill[tipo="ocioso"]      {{ background: #e2e8f0; color: #334155; }}
#statusPill[tipo="ouvindo"]     {{ background: #dcfce7; color: #166534; }}
#statusPill[tipo="trabalhando"] {{ background: #fef3c7; color: #92400e; }}
#statusPill[tipo="falando"]     {{ background: #ede9fe; color: #5b21b6; }}
#statusPill[tipo="ok"]          {{ background: #dbeafe; color: #1e40af; }}
#statusPill[tipo="erro"]        {{ background: #fee2e2; color: #991b1b; }}

#card {{
    background: #ffffff; border: 1px solid #dfe5ef; border-radius: 14px;
}}
#cardTitle {{
    font-size: 12px; font-weight: 700; color: #475569;
    letter-spacing: 0.6px; text-transform: uppercase;
}}
#imageView {{
    background: #0f172a; border-radius: 10px; color: #94a3b8; font-size: 13px;
}}

#questionText {{
    font-size: 16px; color: #0f172a; background: #f8fafc;
    border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px;
}}
#answerText {{
    font-size: 17px; color: #064e3b; background: #ecfdf5;
    border: 1px solid #a7f3d0; border-radius: 10px; padding: 14px;
}}
#answerText[vazio="true"], #questionText[vazio="true"] {{
    color: #94a3b8; background: #f8fafc; border: 1px dashed #cbd5e1;
}}

#micButton {{
    background: {ACCENT}; color: white; border: none; border-radius: 30px;
    font-size: 17px; font-weight: 700; padding: 14px 28px; min-height: 32px;
}}
#micButton:hover {{ background: #1d4ed8; }}
#micButton:disabled {{ background: #94a3b8; }}
#micButton[modo="ouvindo"] {{ background: #16a34a; }}
#micButton[modo="ouvindo"]:hover {{ background: #15803d; }}
#micButton[modo="falando"] {{ background: #7c3aed; }}

QPushButton#secondary {{
    background: #ffffff; color: {ACCENT}; border: 1px solid #bfd0f5;
    border-radius: 8px; padding: 7px 14px; font-weight: 600;
}}
QPushButton#secondary:hover {{ background: #eff4ff; }}
QPushButton#secondary:disabled {{ color: #94a3b8; border-color: #e2e8f0; }}

QLineEdit {{
    background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px;
    padding: 9px 12px; font-size: 14px;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QProgressBar#level {{
    background: #e2e8f0; border: none; border-radius: 4px; max-height: 8px;
}}
QProgressBar#level::chunk {{ background: #22c55e; border-radius: 4px; }}

#step {{
    border-radius: 8px; padding: 7px 4px; font-size: 12px; font-weight: 600;
    background: #f1f5f9; color: #94a3b8;
}}
#step[estado="ativo"]  {{ background: #fef3c7; color: #92400e; }}
#step[estado="feito"]  {{ background: #dcfce7; color: #166534; }}
#step[estado="erro"]   {{ background: #fee2e2; color: #991b1b; }}
#step[estado="pulado"] {{ background: #f8fafc; color: #cbd5e1; }}
#stepArrow {{ color: #cbd5e1; font-size: 16px; }}

#errorBanner {{
    background: #fef2f2; color: #991b1b; border: 1px solid #fecaca;
    border-radius: 10px; padding: 10px 14px;
}}
#warnBanner {{
    background: #fffbeb; color: #92400e; border: 1px solid #fde68a;
    border-radius: 10px; padding: 10px 14px;
}}

QListWidget {{
    border: none; background: transparent; font-size: 13px;
}}
QListWidget::item {{ padding: 6px 4px; border-bottom: 1px solid #f1f5f9; }}
QListWidget::item:selected {{ background: #eff4ff; color: #1e3a8a; }}

#historyList {{ background: #ffffff; border-radius: 8px; }}
#historyList::item {{ padding: 8px 6px; border-bottom: 1px solid #f1f5f9; }}
#historyDialog {{ background: #eef2f8; }}

QStatusBar {{ background: #e2e8f0; color: #475569; font-size: 12px; }}
#camBadge {{ font-size: 12px; font-weight: 600; }}
#hint {{ color: #64748b; font-size: 12px; }}
"""
