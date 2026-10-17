"""Página Ajustes: provedor, chave, modelos, câmera, áudio, voz e gravação.

Salva no .env (só as chaves alteradas, preservando o resto) e aplica na hora, sem reiniciar.
A chave da API nunca é exibida: o campo fica vazio e só é gravado se você digitar uma nova.
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractSpinBox, QComboBox, QDoubleSpinBox, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from .. import env_file
from ..config import CHAVE_POR_PROVEDOR, PADROES_PROVEDOR, Config, parse_camera_source
from .widgets import Card, Toggle

NOMES_PROVEDOR = {"gemini": "Gemini (Google) — tem camada gratuita", "openai": "OpenAI — exige créditos"}
LARGURA_ROTULO = 240
CAMPOS_MODELO = (("vision_model", "MODELO_VISAO"), ("stt_model", "MODELO_STT"),
                 ("tts_model", "MODELO_TTS"), ("tts_voice", "VOZ_TTS"))


def _bool(valor: bool) -> str:
    return "true" if valor else "false"


class SettingsPage(QScrollArea):
    def __init__(self, config: Config, on_apply: Callable[[Config], bool],
                 parent: QWidget | None = None):
        """`on_apply(novo_config)` aplica no app e devolve False se não for possível agora."""
        super().__init__(parent)
        self.setObjectName("page")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.config = config
        self.on_apply = on_apply
        # chaves conhecidas por provedor (do .env/ambiente e as salvas aqui); nunca exibidas
        self._chaves = {p: os.environ.get(v) or None for p, v in CHAVE_POR_PROVEDOR.items()}
        if config.api_key:
            self._chaves[config.provider] = config.api_key

        corpo = QWidget(objectName="pageBody")
        self.setWidget(corpo)
        lay = QVBoxLayout(corpo)
        lay.setContentsMargins(32, 26, 32, 26)
        lay.setSpacing(16)

        topo = QHBoxLayout()
        titulos = QVBoxLayout()
        titulos.setSpacing(4)
        titulos.addWidget(QLabel("Ajustes", objectName="pageTitle"))
        sub = QLabel("As mudanças são salvas no arquivo .env e aplicadas na hora.",
                     objectName="pageSubtitle")
        sub.setWordWrap(True)
        titulos.addWidget(sub)
        topo.addLayout(titulos, 1)
        self.discard_button = QPushButton("Descartar", objectName="secondary")
        self.discard_button.setCursor(Qt.PointingHandCursor)
        self.discard_button.clicked.connect(self.load)
        self.save_button = QPushButton("Salvar alterações", objectName="primary")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.save)
        topo.addWidget(self.discard_button, 0, Qt.AlignVCenter)
        topo.addWidget(self.save_button, 0, Qt.AlignVCenter)
        lay.addLayout(topo)

        self.status = QLabel(objectName="settingsStatus")
        self.status.setWordWrap(True)
        self.status.hide()
        lay.addWidget(self.status)

        # --- provedor
        provedor = Card("Provedor de IA")
        form = self._form(provedor)
        self.provider = QComboBox()
        for chave, nome in NOMES_PROVEDOR.items():
            self.provider.addItem(nome, chave)
        self.provider.setMinimumWidth(360)
        self.provider.currentIndexChanged.connect(self._on_provider_changed)
        self._linha(form, "Provedor", self.provider)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setClearButtonEnabled(True)
        self._linha(form, "Chave da API", self.api_key)
        self.key_hint = QLabel(objectName="hint")
        self.key_hint.setWordWrap(True)
        self.key_hint.setContentsMargins(LARGURA_ROTULO + 18, 0, 0, 0)  # alinhado aos campos
        provedor.add(self.key_hint)
        lay.addWidget(provedor)

        # --- modelos
        modelos = Card("Modelos")
        self.defaults_button = QPushButton("Restaurar padrões", objectName="secondary")
        self.defaults_button.setCursor(Qt.PointingHandCursor)
        self.defaults_button.clicked.connect(self._restaurar_padroes)
        modelos.acoes.addWidget(self.defaults_button)
        form = self._form(modelos)
        self.vision_model, self.stt_model = QLineEdit(), QLineEdit()
        self.tts_model, self.tts_voice = QLineEdit(), QLineEdit()
        self._linha(form, "Visão (imagem + pergunta)", self.vision_model)
        self._linha(form, "Transcrição da fala", self.stt_model)
        self._linha(form, "Voz (síntese)", self.tts_model)
        self._linha(form, "Nome da voz", self.tts_voice)
        lay.addWidget(modelos)

        # --- câmera e áudio
        midia = Card("Câmera e microfone")
        form = self._form(midia)
        self.camera = QLineEdit()
        self.camera.setPlaceholderText("0 = webcam padrão, 1 = segunda webcam, ou caminho de vídeo/imagem")
        self._linha(form, "Câmera", self.camera)
        self.silence = self._spin(0.3, 5.0, 0.1, " s")
        self._linha(form, "Silêncio que encerra a pergunta", self.silence)
        self.max_record = self._spin(3, 60, 1, " s")
        self._linha(form, "Duração máxima da pergunta", self.max_record)
        lay.addWidget(midia)

        # --- voz e gravação
        extras = Card("Voz e conversas")
        self.tts_enabled = Toggle("Falar as respostas em voz alta")
        self.offline_voice = Toggle("Usar a voz do computador se a voz online falhar")
        self.save_history = Toggle("Salvar as conversas automaticamente")
        for caixa in (self.tts_enabled, self.offline_voice, self.save_history):
            caixa.setCursor(Qt.PointingHandCursor)
            extras.add(caixa)
        lay.addWidget(extras)
        lay.addStretch(1)

        self.load()

    # ================================================================ util
    @staticmethod
    def _form(card: Card) -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        card._layout.addLayout(form)
        return form

    @staticmethod
    def _linha(form: QFormLayout, texto: str, campo: QWidget) -> None:
        rotulo = QLabel(texto)
        rotulo.setFixedWidth(LARGURA_ROTULO)  # alinha os campos de todos os cartões
        rotulo.setWordWrap(True)
        form.addRow(rotulo, campo)

    @staticmethod
    def _spin(minimo: float, maximo: float, passo: float, sufixo: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimo, maximo)
        spin.setSingleStep(passo)
        spin.setDecimals(1)
        spin.setSuffix(sufixo)
        spin.setFixedWidth(120)
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)  # digita ou usa a roda do mouse
        return spin

    @property
    def provedor(self) -> str:
        return self.provider.currentData()

    # ============================================================ carregar
    def load(self) -> None:
        """Preenche os campos com a configuração em uso (também serve para descartar)."""
        c = self.config
        self.provider.blockSignals(True)
        self.provider.setCurrentIndex(max(0, self.provider.findData(c.provider)))
        self.provider.blockSignals(False)
        self._anterior = c.provider
        self.api_key.clear()
        for atributo, _ in CAMPOS_MODELO:
            getattr(self, atributo).setText(getattr(c, atributo))
        self.camera.setText(str(c.camera_source))
        self.silence.setValue(c.silence_seconds)
        self.max_record.setValue(c.max_record_seconds)
        self.tts_enabled.setChecked(c.tts_enabled)
        self.offline_voice.setChecked(c.tts_offline_fallback)
        self.save_history.setChecked(c.save_history)
        self._atualizar_dica_chave()
        self.status.hide()

    def _chave_existente(self, provedor: str) -> str | None:
        return self._chaves.get(provedor)

    def _atualizar_dica_chave(self) -> None:
        variavel = CHAVE_POR_PROVEDOR[self.provedor]
        if self._chave_existente(self.provedor):
            self.api_key.setPlaceholderText("•••••••• configurada — deixe vazio para manter")
            self.key_hint.setText(f"Salva em {variavel}. Por segurança, a chave atual não é exibida.")
        else:
            self.api_key.setPlaceholderText("cole aqui a sua chave")
            link = ("aistudio.google.com/apikey" if self.provedor == "gemini"
                    else "platform.openai.com/api-keys")
            self.key_hint.setText(f"Nenhuma chave configurada para este provedor. Gere em {link}.")

    def _on_provider_changed(self) -> None:
        # troca para os modelos do novo provedor os campos que estavam no padrão do anterior
        antigos, novos = PADROES_PROVEDOR[self._anterior], PADROES_PROVEDOR[self.provedor]
        for atributo, _ in CAMPOS_MODELO:
            campo = getattr(self, atributo)
            if campo.text().strip() in ("", antigos[atributo]):
                campo.setText(novos[atributo])
        self._anterior = self.provedor
        self._atualizar_dica_chave()

    def _restaurar_padroes(self) -> None:
        for atributo, _ in CAMPOS_MODELO:
            getattr(self, atributo).setText(PADROES_PROVEDOR[self.provedor][atributo])

    # ============================================================== salvar
    def _mostrar(self, estado: str, texto: str) -> None:
        self.status.setText(texto)
        self.status.setProperty("estado", estado)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.show()

    def novo_config(self) -> Config:
        provedor = self.provedor
        padroes = PADROES_PROVEDOR[provedor]
        chave = self.api_key.text().strip() or self._chave_existente(provedor)
        modelos = {a: getattr(self, a).text().strip() or padroes[a] for a, _ in CAMPOS_MODELO}
        return replace(
            self.config, provider=provedor, api_key=chave,
            base_url=self.config.base_url if provedor == self.config.provider else padroes["base_url"],
            camera_source=parse_camera_source(self.camera.text()),
            silence_seconds=round(self.silence.value(), 1),
            max_record_seconds=round(self.max_record.value(), 1),
            tts_enabled=self.tts_enabled.isChecked(),
            tts_offline_fallback=self.offline_voice.isChecked(),
            save_history=self.save_history.isChecked(),
            **modelos)

    def valores_env(self, novo: Config) -> dict[str, str]:
        """Chaves do .env a gravar. Modelos no padrão do provedor ficam vazios, para que trocar
        de provedor depois (mesmo editando o .env à mão) use os modelos certos."""
        padroes = PADROES_PROVEDOR[novo.provider]
        valores = {"PROVEDOR": novo.provider}
        for atributo, variavel in CAMPOS_MODELO:
            valor = getattr(novo, atributo)
            valores[variavel] = "" if valor == padroes[atributo] else valor
        valores.update({
            "CAMERA": str(novo.camera_source),
            "SILENCIO_SEG": f"{novo.silence_seconds:g}",
            "GRAVACAO_MAX_SEG": f"{novo.max_record_seconds:g}",
            "TTS_ATIVO": _bool(novo.tts_enabled),
            "TTS_OFFLINE_FALLBACK": _bool(novo.tts_offline_fallback),
            "SALVAR_HISTORICO": _bool(novo.save_history),
        })
        digitada = self.api_key.text().strip()
        if digitada:
            valores[CHAVE_POR_PROVEDOR[novo.provider]] = digitada
        return valores

    def save(self) -> None:
        if not self.camera.text().strip():
            self._mostrar("erro", "Informe a câmera: 0 para a webcam padrão, ou um caminho.")
            return
        novo = self.novo_config()
        valores = self.valores_env(novo)
        if not self.on_apply(novo):
            self._mostrar("erro", "Aguarde a pergunta atual terminar para salvar os ajustes.")
            return
        try:
            env_file.update_env(novo.env_path, valores)
        except OSError as exc:
            self._mostrar("erro", f"Os ajustes valem até fechar o app, mas não foi possível salvar "
                                  f"em {novo.env_path}: {exc}")
            self.config = novo
            return
        if novo.api_key:
            self._chaves[novo.provider] = novo.api_key
        self.config = novo
        self.load()
        aviso = "" if novo.api_key else " Falta a chave da API deste provedor."
        self._mostrar("ok", f"Ajustes salvos e aplicados.{aviso}")
