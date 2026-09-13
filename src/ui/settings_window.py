"""
Modern Settings & Control Panel for Dictatly Windows.
Follows Apple macOS Sequoia System Settings design language:
- Warm graphite/titanium palette (no harsh pitch black, no AI-slop)
- Native SF Pro / Segoe UI Variable typography with sentence-case hierarchy
- Tactile Apple Chiclet Keycaps with modifier glyphs (⌃, ⌥, ⇧, ⊞)
- In-place instant language switching (RU / EN) without window crash
- App squircle icon in header and window title
"""

import math
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import (
    QIcon, QFont, QColor, QPainter, QBrush, QPen,
    QLinearGradient, QPainterPath, QPixmap
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QComboBox, QCheckBox,
    QFileDialog
)

from ..localization import t
from ..config import AppConfig
from ..core.hotkey import GlobalHotkeyManager
from ..core.audio import AudioRecorder
from ..core.security import encrypt_secret, decrypt_secret
from ..engine.ai_cleaner import AICleaner

# Keycap modifier glyph mappings (Apple style)
KEY_GLYPHS = {
    "VK_RCONTROL": "⌃ Right Ctrl",
    "VK_LCONTROL": "⌃ Left Ctrl",
    "VK_RMENU": "⌥ Right Alt",
    "VK_LMENU": "⌥ Left Alt",
    "VK_RSHIFT": "⇧ Right Shift",
    "VK_LSHIFT": "⇧ Left Shift",
    "VK_RWIN": "⊞ Right Win",
    "VK_LWIN": "⊞ Left Win",
    "VK_CAPITAL": "⇪ Caps Lock",
    "VK_SPACE": "␣ Space",
    "VK_RETURN": "↵ Enter",
    "VK_ESCAPE": "⎋ Esc",
    "VK_TAB": "⇥ Tab",
}

def format_keycap_text(combo: str) -> str:
    """Format key combo into stylish keycap text with symbols."""
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    formatted = [KEY_GLYPHS.get(p, p.replace("VK_", "")) for p in parts]
    return " + ".join(formatted)

class KeycapButton(QPushButton):
    """Tactile Apple chiclet keycap button with subtle bevel and active recording state."""
    def __init__(self, combo: str, theme: str = "dark"):
        super().__init__()
        self.combo = combo
        self.theme = theme
        self.is_recording = False
        self.pulse_phase = 0.0

        self.setFixedHeight(28)
        self.setMinimumWidth(115)
        self.setCursor(Qt.PointingHandCursor)
        self._update_text()

        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(30)
        self.pulse_timer.timeout.connect(self._on_pulse)

    def set_combo(self, combo: str):
        self.combo = combo
        self._update_text()

    def set_theme(self, theme: str):
        self.theme = theme
        self.update()

    def set_recording(self, recording: bool):
        self.is_recording = recording
        if recording:
            self.pulse_timer.start()
        else:
            self.pulse_timer.stop()
            self._update_text()
        self.update()

    def _update_text(self):
        self.setText(format_keycap_text(self.combo))

    def _on_pulse(self):
        self.pulse_phase = (self.pulse_phase + 0.12)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 5.0, 5.0)

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())

        if self.is_recording:
            # Active recording state: subtle white breath
            pulse_alpha = int(35 + abs(math.sin(self.pulse_phase)) * 40)
            painter.fillPath(path, QBrush(QColor(255, 255, 255, pulse_alpha)))
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1.0))
            painter.drawPath(path)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("-apple-system", 9, QFont.DemiBold))
            painter.drawText(rect, Qt.AlignCenter, "Нажмите клавишу...")
            return

        if self.theme == "dark":
            grad.setColorAt(0.0, QColor(56, 56, 60))
            grad.setColorAt(1.0, QColor(44, 44, 48))
            border_pen = QPen(QColor(255, 255, 255, 30), 1.0)
            text_color = QColor(245, 245, 247)
        else:
            grad.setColorAt(0.0, QColor(255, 255, 255))
            grad.setColorAt(1.0, QColor(240, 240, 244))
            border_pen = QPen(QColor(0, 0, 0, 35), 1.0)
            text_color = QColor(28, 28, 30)

        painter.fillPath(path, QBrush(grad))
        painter.setPen(border_pen)
        painter.drawPath(path)

        painter.setPen(text_color)
        font = QFont("-apple-system", 9)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())

class SettingsCard(QFrame):
    """Grouped card container in Apple macOS Sequoia style."""
    def __init__(self, theme: str = "dark"):
        super().__init__()
        self.setObjectName("SettingsCard")
        self.set_theme(theme)

    def set_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet("""
                #SettingsCard {
                    background-color: #28282A;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                #SettingsCard {
                    background-color: #FFFFFF;
                    border: 1px solid rgba(0, 0, 0, 0.07);
                    border-radius: 10px;
                }
            """)

class SettingsWindow(QWidget):
    settings_saved = Signal()
    restart_service_requested = Signal()

    def __init__(self, config: AppConfig, hotkey_mgr: GlobalHotkeyManager):
        super().__init__()
        self.config = config
        self.hotkey_mgr = hotkey_mgr
        self.current_recording_target = None
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Set Window Icon
        res_dir = Path(__file__).resolve().parent.parent.parent / "resources"
        icon_path = res_dir / "app_icon_64.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setMinimumSize(540, 680)
        self.resize(560, 710)

        self._init_ui()
        self.retranslate_ui()

    def _init_ui(self):
        theme = self.config["capsule_theme"]

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Scrollable Settings Body ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        body_widget = QWidget()
        body_widget.setObjectName("BodyWidget")
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(20, 14, 20, 14)
        body_layout.setSpacing(14)

        # === Card 1: Горячие клавиши (Hotkeys) ===
        self.hdr_hotkeys = self._create_section_header("")
        body_layout.addWidget(self.hdr_hotkeys)

        self.card_hotkeys = SettingsCard(theme)
        card_hk_layout = QVBoxLayout(self.card_hotkeys)
        card_hk_layout.setContentsMargins(16, 12, 16, 12)
        card_hk_layout.setSpacing(12)

        # Hotkey Main
        hk_main_w, self.lbl_hk_main, self.hint_hk_main = self._create_hotkey_row(
            combo_val=self.config["hotkey_main"],
            target="main",
            theme=theme
        )
        card_hk_layout.addWidget(hk_main_w)
        card_hk_layout.addWidget(self._create_divider(theme))

        # Hotkey Alt
        hk_alt_w, self.lbl_hk_alt, self.hint_hk_alt = self._create_hotkey_row(
            combo_val=self.config["hotkey_alt"],
            target="alt",
            theme=theme
        )
        card_hk_layout.addWidget(hk_alt_w)
        card_hk_layout.addWidget(self._create_divider(theme))

        # Hotkey History
        hk_hist_w, self.lbl_hk_history, self.hint_hk_history = self._create_hotkey_row(
            combo_val=self.config["hotkey_history"],
            target="history",
            theme=theme
        )
        card_hk_layout.addWidget(hk_hist_w)
        body_layout.addWidget(self.card_hotkeys)

        # === Card 2: Поведение при вставке (Behavior) ===
        self.hdr_behavior = self._create_section_header("")
        body_layout.addWidget(self.hdr_behavior)

        self.card_behavior = SettingsCard(theme)
        card_b_layout = QVBoxLayout(self.card_behavior)
        card_b_layout.setContentsMargins(16, 12, 16, 12)
        card_b_layout.setSpacing(12)

        self.chk_enter = QCheckBox()
        self.chk_enter.setChecked(self.config["enter_after_insert"])
        card_b_layout.addWidget(self.chk_enter)
        card_b_layout.addWidget(self._create_divider(theme))

        suffix_row = QHBoxLayout()
        self.lbl_suffix = QLabel()
        self.combo_suffix = QComboBox()
        self.combo_suffix.setMaximumWidth(160)
        self.combo_suffix.addItem("", "space")
        self.combo_suffix.addItem("", "none")
        self.combo_suffix.addItem("", "newline")
        s_idx = self.combo_suffix.findData(self.config["paste_suffix"])
        if s_idx >= 0:
            self.combo_suffix.setCurrentIndex(s_idx)

        suffix_row.addWidget(self.lbl_suffix)
        suffix_row.addStretch()
        suffix_row.addWidget(self.combo_suffix)
        card_b_layout.addLayout(suffix_row)
        body_layout.addWidget(self.card_behavior)

        # === Card 3: Аудио и Микрофон (Audio & Export) ===
        self.hdr_audio = self._create_section_header("")
        body_layout.addWidget(self.hdr_audio)

        self.card_audio = SettingsCard(theme)
        card_a_layout = QVBoxLayout(self.card_audio)
        card_a_layout.setContentsMargins(16, 12, 16, 12)
        card_a_layout.setSpacing(12)

        mic_row = QHBoxLayout()
        self.lbl_mic = QLabel()
        self.combo_mic = QComboBox()
        self.combo_mic.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_mic.setMinimumContentsLength(18)
        self.combo_mic.setMaximumWidth(280)
        self.combo_mic.addItem("", None)
        devices = AudioRecorder.get_input_devices()
        cur_dev = self.config["microphone_device"]
        for d in devices:
            clean_name = d["name"].replace("\r", " ").replace("\n", " ").strip()
            if len(clean_name) > 40:
                clean_name = clean_name[:37] + "..."
            self.combo_mic.addItem(clean_name, d["index"])
            if cur_dev == d["index"]:
                self.combo_mic.setCurrentIndex(self.combo_mic.count() - 1)
        mic_row.addWidget(self.lbl_mic)
        mic_row.addStretch()
        mic_row.addWidget(self.combo_mic)
        card_a_layout.addLayout(mic_row)

        card_a_layout.addWidget(self._create_divider(theme))

        export_row = QHBoxLayout()
        self.lbl_export = QLabel()
        self.txt_export_folder = QLineEdit(self.config["export_folder"])
        self.txt_export_folder.setReadOnly(True)
        self.btn_browse = QPushButton()
        self.btn_browse.clicked.connect(self._browse_export_folder)
        export_row.addWidget(self.lbl_export)
        export_row.addWidget(self.txt_export_folder, 1)
        export_row.addWidget(self.btn_browse)
        card_a_layout.addLayout(export_row)
        body_layout.addWidget(self.card_audio)

        # === Card 4: Локальное распознавание (ASR Engine) ===
        self.hdr_model = self._create_section_header("")
        body_layout.addWidget(self.hdr_model)

        self.card_model = SettingsCard(theme)
        card_m_layout = QVBoxLayout(self.card_model)
        card_m_layout.setContentsMargins(16, 12, 16, 12)
        card_m_layout.setSpacing(12)

        m_row = QHBoxLayout()
        self.lbl_model = QLabel()
        self.combo_model = QComboBox()
        self.combo_model.setMaximumWidth(280)
        self.combo_model.addItem("large-v3-turbo (Fast & Accurate)", "large-v3-turbo")
        self.combo_model.addItem("small (Lightweight)", "small")
        self.combo_model.addItem("base (Minimal)", "base")
        midx = self.combo_model.findData(self.config["whisper_model"])
        if midx >= 0:
            self.combo_model.setCurrentIndex(midx)
        m_row.addWidget(self.lbl_model)
        m_row.addStretch()
        m_row.addWidget(self.combo_model)
        card_m_layout.addLayout(m_row)

        card_m_layout.addWidget(self._create_divider(theme))

        lang_row = QHBoxLayout()
        self.lbl_dict_lang = QLabel()
        self.combo_dict_lang = QComboBox()
        self.combo_dict_lang.setMaximumWidth(160)
        self.combo_dict_lang.addItem("", "auto")
        self.combo_dict_lang.addItem("", "ru")
        self.combo_dict_lang.addItem("", "en")
        lidx = self.combo_dict_lang.findData(self.config["dictation_language"])
        if lidx >= 0:
            self.combo_dict_lang.setCurrentIndex(lidx)
        lang_row.addWidget(self.lbl_dict_lang)
        lang_row.addStretch()
        lang_row.addWidget(self.combo_dict_lang)
        card_m_layout.addLayout(lang_row)
        body_layout.addWidget(self.card_model)

        # === Card 5: Внешний вид (HUD) ===
        self.hdr_hud = self._create_section_header("")
        body_layout.addWidget(self.hdr_hud)

        self.card_hud = SettingsCard(theme)
        card_h_layout = QHBoxLayout(self.card_hud)
        card_h_layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_size = QLabel()
        self.combo_size = QComboBox()
        self.combo_size.setMaximumWidth(140)
        self.combo_size.addItem("Компактный (S)", "small")
        self.combo_size.addItem("Стандартный (M)", "medium")
        self.combo_size.addItem("Крупный (L)", "large")
        sidx = self.combo_size.findData(self.config["capsule_size"])
        if sidx >= 0:
            self.combo_size.setCurrentIndex(sidx)

        self.lbl_theme = QLabel()
        self.combo_theme = QComboBox()
        self.combo_theme.setMaximumWidth(140)
        self.combo_theme.addItem("", "dark")
        self.combo_theme.addItem("", "light")
        tidx = self.combo_theme.findData(self.config["capsule_theme"])
        if tidx >= 0:
            self.combo_theme.setCurrentIndex(tidx)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)

        card_h_layout.addWidget(self.lbl_size)
        card_h_layout.addWidget(self.combo_size)
        card_h_layout.addSpacing(20)
        card_h_layout.addWidget(self.lbl_theme)
        card_h_layout.addWidget(self.combo_theme)
        card_h_layout.addStretch()
        body_layout.addWidget(self.card_hud)

        # === Card 6: AI-чистка текста (Optional) ===
        self.hdr_ai = self._create_section_header("")
        body_layout.addWidget(self.hdr_ai)

        self.card_ai = SettingsCard(theme)
        card_ai_layout = QVBoxLayout(self.card_ai)
        card_ai_layout.setContentsMargins(16, 12, 16, 12)
        card_ai_layout.setSpacing(10)

        self.lbl_ai_desc = QLabel()
        self.lbl_ai_desc.setStyleSheet("color: #86868B; font-size: 11px;")
        self.lbl_ai_desc.setWordWrap(True)
        card_ai_layout.addWidget(self.lbl_ai_desc)

        self.chk_ai = QCheckBox()
        self.chk_ai.setChecked(self.config["ai_cleanup_enabled"])
        card_ai_layout.addWidget(self.chk_ai)
        card_ai_layout.addWidget(self._create_divider(theme))

        ai_url_row = QHBoxLayout()
        self.lbl_ai_url = QLabel()
        self.txt_ai_url = QLineEdit(self.config["ai_base_url"])
        ai_url_row.addWidget(self.lbl_ai_url)
        ai_url_row.addWidget(self.txt_ai_url, 1)
        card_ai_layout.addLayout(ai_url_row)

        ai_model_row = QHBoxLayout()
        self.lbl_ai_model = QLabel()
        self.txt_ai_model = QLineEdit(self.config["ai_model"])
        ai_model_row.addWidget(self.lbl_ai_model)
        ai_model_row.addWidget(self.txt_ai_model, 1)
        card_ai_layout.addLayout(ai_model_row)

        ai_key_row = QHBoxLayout()
        self.lbl_ai_key = QLabel()
        self.txt_ai_key = QLineEdit()
        self.txt_ai_key.setEchoMode(QLineEdit.Password)
        decrypted = decrypt_secret(self.config["ai_api_key_encrypted"])
        if decrypted:
            self.txt_ai_key.setText(decrypted)

        self.btn_test_conn = QPushButton()
        self.btn_test_conn.clicked.connect(self._test_ai_connection)

        ai_key_row.addWidget(self.lbl_ai_key)
        ai_key_row.addWidget(self.txt_ai_key, 1)
        ai_key_row.addWidget(self.btn_test_conn)
        card_ai_layout.addLayout(ai_key_row)

        self.lbl_conn_status = QLabel("")
        self.lbl_conn_status.setStyleSheet("font-size: 11px;")
        card_ai_layout.addWidget(self.lbl_conn_status)
        body_layout.addWidget(self.card_ai)

        scroll.setWidget(body_widget)
        root_layout.addWidget(scroll, 1)

        # --- Footer Actions ---
        footer_frame = QFrame()
        footer_frame.setObjectName("FooterFrame")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(20, 12, 20, 12)

        self.btn_restart = QPushButton()
        self.btn_restart.clicked.connect(self.restart_service_requested.emit)
        footer_layout.addWidget(self.btn_restart)

        # Language Segmented Pill button
        self.btn_lang = QPushButton()
        self.btn_lang.setToolTip("Switch Language (RU / EN)")
        self.btn_lang.setFixedWidth(46)
        self.btn_lang.setFixedHeight(28)
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.clicked.connect(self._toggle_language)
        footer_layout.addWidget(self.btn_lang)

        footer_layout.addStretch()

        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self.close)
        footer_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton()
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_settings)
        footer_layout.addWidget(self.btn_save)

        root_layout.addWidget(footer_frame)
        self._apply_global_theme(theme)

    def retranslate_ui(self):
        """Update all text in-place when language toggles without crashing or closing."""
        lang = self.config["interface_language"]

        # Window Title
        self.setWindowTitle(t("settings_title", lang))

        # Language toggle button
        self.btn_lang.setText(lang.upper())

        # Section Headers (Clean sentence case, Apple style)
        self.hdr_hotkeys.setText(t("hotkeys_section", lang))
        self.hdr_behavior.setText(t("behavior_section", lang))
        self.hdr_audio.setText(t("audio_section", lang))
        self.hdr_model.setText(t("model_section", lang))
        self.hdr_hud.setText(t("hud_section", lang))
        self.hdr_ai.setText(t("ai_cleanup_section", lang))

        # Hotkeys
        self.lbl_hk_main.setText(t("hotkey_main", lang) + ":")
        self.hint_hk_main.setText(t("hotkey_main_hint", lang))
        self.lbl_hk_alt.setText(t("hotkey_alt", lang) + ":")
        self.hint_hk_alt.setText(t("hotkey_alt_hint", lang))
        self.lbl_hk_history.setText(t("hotkey_history", lang) + ":")
        self.hint_hk_history.setText(t("hotkey_history_hint", lang))

        # Behavior
        self.chk_enter.setText(t("enter_after_insert", lang))
        self.lbl_suffix.setText(t("paste_suffix", lang) + ":")
        self.combo_suffix.setItemText(0, t("suffix_space", lang))
        self.combo_suffix.setItemText(1, t("suffix_none", lang))
        self.combo_suffix.setItemText(2, t("suffix_newline", lang))

        # Audio
        self.lbl_mic.setText(t("microphone_select", lang) + ":")
        self.combo_mic.setItemText(0, t("default_mic", lang))
        self.lbl_export.setText(t("export_folder", lang) + ":")
        self.btn_browse.setText(t("choose_folder", lang))

        # Model
        self.lbl_model.setText(t("model_name", lang) + ":")
        self.lbl_dict_lang.setText(t("dictation_language", lang) + ":")
        self.combo_dict_lang.setItemText(0, t("lang_auto", lang))
        self.combo_dict_lang.setItemText(1, t("lang_ru", lang))
        self.combo_dict_lang.setItemText(2, t("lang_en", lang))

        # HUD
        self.lbl_size.setText(t("capsule_size", lang) + ":")
        self.lbl_theme.setText(t("capsule_theme", lang) + ":")
        self.combo_theme.setItemText(0, t("theme_dark", lang))
        self.combo_theme.setItemText(1, t("theme_light", lang))

        # AI
        self.lbl_ai_desc.setText(t("ai_cleanup_desc", lang))
        self.chk_ai.setText(t("enable_ai_cleanup", lang))
        self.lbl_ai_url.setText(t("api_base_url", lang) + ":")
        self.lbl_ai_model.setText(t("api_model", lang) + ":")
        self.lbl_ai_key.setText(t("api_key", lang) + ":")
        self.btn_test_conn.setText(t("test_connection", lang))

        # Footer
        self.btn_restart.setText(t("restart_service", lang))
        self.btn_cancel.setText(t("cancel", lang))
        self.btn_save.setText(t("save_and_restart", lang))

    def _create_section_header(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #86868B; letter-spacing: 0.1px; margin-top: 4px; margin-left: 2px;")
        return lbl

    def _create_divider(self, theme: str = "dark") -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        color = "rgba(255, 255, 255, 0.06)" if theme == "dark" else "rgba(0, 0, 0, 0.06)"
        line.setStyleSheet(f"background-color: {color}; border: none; min-height: 1px; max-height: 1px;")
        return line

    def _create_hotkey_row(self, combo_val: str, target: str, theme: str):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)

        row = QHBoxLayout()
        title_lbl = QLabel()
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 500;")

        keycap = KeycapButton(combo_val, theme=theme)
        keycap.clicked.connect(lambda: self._start_recording_hotkey(target, keycap))
        setattr(self, f"btn_hotkey_{target}", keycap)
        setattr(self, f"val_hotkey_{target}", combo_val)

        row.addWidget(title_lbl)
        row.addStretch()
        row.addWidget(keycap)
        l.addLayout(row)

        hint_lbl = QLabel()
        hint_lbl.setStyleSheet("color: #86868B; font-size: 11px;")
        l.addWidget(hint_lbl)
        return w, title_lbl, hint_lbl

    def _start_recording_hotkey(self, target: str, keycap: KeycapButton):
        self.current_recording_target = target
        keycap.set_recording(True)

        def on_recorded(combo: str):
            setattr(self, f"val_hotkey_{target}", combo)
            QTimer.singleShot(0, lambda: self._finish_recording_hotkey(target, combo, keycap))

        self.hotkey_mgr.on_hotkey_recorded = on_recorded
        self.hotkey_mgr.is_recording_new_hotkey = True

    def _finish_recording_hotkey(self, target: str, combo: str, keycap: KeycapButton):
        self.hotkey_mgr.is_recording_new_hotkey = False
        self.hotkey_mgr.on_hotkey_recorded = None
        keycap.set_combo(combo)
        keycap.set_recording(False)

    def _browse_export_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выбор папки", self.txt_export_folder.text())
        if folder:
            self.txt_export_folder.setText(folder)

    def _test_ai_connection(self):
        lang = self.config["interface_language"]
        url = self.txt_ai_url.text().strip()
        model = self.txt_ai_model.text().strip()
        key = self.txt_ai_key.text().strip()

        self.lbl_conn_status.setText("Проверка подключения...")
        self.lbl_conn_status.setStyleSheet("color: #86868B;")

        cleaner = AICleaner(base_url=url, model=model, api_key=key)
        ok, msg = cleaner.test_connection()
        if ok:
            self.lbl_conn_status.setText(f"✓ {t('connection_ok', lang)}")
            self.lbl_conn_status.setStyleSheet("color: #34C759; font-weight: 500;")
        else:
            self.lbl_conn_status.setText(f"✗ {t('connection_failed', lang)}: {msg}")
            self.lbl_conn_status.setStyleSheet("color: #FF453A;")

    def _toggle_language(self):
        new_lang = "en" if self.config["interface_language"] == "ru" else "ru"
        self.config["interface_language"] = new_lang
        self.config.save()
        self.retranslate_ui()

    def _on_theme_changed(self, idx: int):
        new_theme = self.combo_theme.currentData()
        self._apply_global_theme(new_theme)
        for card in [self.card_hotkeys, self.card_behavior, self.card_audio, self.card_model, self.card_hud, self.card_ai]:
            card.set_theme(new_theme)
        for target in ["main", "alt", "history"]:
            btn = getattr(self, f"btn_hotkey_{target}", None)
            if btn:
                btn.set_theme(new_theme)

    def _apply_global_theme(self, theme: str):
        if theme == "dark":
            # Apple macOS Warm Graphite Dark
            self.setStyleSheet("""
                SettingsWindow, QScrollArea, #BodyWidget {
                    background-color: #1E1E20;
                    color: #F5F5F7;
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", sans-serif;
                }
                #HeaderFrame {
                    background-color: #242426;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
                }
                #FooterFrame {
                    background-color: #242426;
                    border-top: 1px solid rgba(255, 255, 255, 0.07);
                }
                QLabel {
                    color: #F5F5F7;
                    font-size: 13px;
                }
                QLineEdit, QComboBox {
                    background-color: #1A1A1D;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 5px 10px;
                    color: #FFFFFF;
                    font-size: 13px;
                }
                QLineEdit:focus, QComboBox:focus {
                    border: 1px solid rgba(255, 255, 255, 0.35);
                }
                QComboBox::drop-down {
                    border: none;
                    padding-right: 8px;
                }
                QPushButton {
                    background-color: #323236;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                    padding: 5px 12px;
                    color: #F5F5F7;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3C3C40;
                }
                QCheckBox {
                    color: #F5F5F7;
                    font-size: 13px;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    background-color: #1A1A1D;
                }
                QCheckBox::indicator:checked {
                    background-color: #FFFFFF;
                    border: 1px solid #FFFFFF;
                    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
                }
            """)
            self.btn_save.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #000000;
                    font-weight: 600;
                    padding: 6px 18px;
                    border-radius: 6px;
                    border: none;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #E5E5EA;
                }
            """)
            self.btn_lang.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D30;
                    color: #FFFFFF;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 13px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #38383D;
                }
            """)
        else:
            # Apple macOS Light Titanium
            self.setStyleSheet("""
                SettingsWindow, QScrollArea, #BodyWidget {
                    background-color: #ECECEC;
                    color: #1D1D1F;
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", sans-serif;
                }
                #HeaderFrame {
                    background-color: #F6F6F8;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
                }
                #FooterFrame {
                    background-color: #F6F6F8;
                    border-top: 1px solid rgba(0, 0, 0, 0.08);
                }
                QLabel {
                    color: #1D1D1F;
                    font-size: 13px;
                }
                QLineEdit, QComboBox {
                    background-color: #FFFFFF;
                    border: 1px solid rgba(0, 0, 0, 0.14);
                    border-radius: 6px;
                    padding: 5px 10px;
                    color: #1D1D1F;
                    font-size: 13px;
                }
                QLineEdit:focus, QComboBox:focus {
                    border: 1px solid #000000;
                }
                QPushButton {
                    background-color: #E5E5EA;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 6px;
                    padding: 5px 12px;
                    color: #1D1D1F;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #DADAE0;
                }
                QCheckBox {
                    color: #1D1D1F;
                    font-size: 13px;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid #C7C7CC;
                    background-color: #FFFFFF;
                }
                QCheckBox::indicator:checked {
                    background-color: #000000;
                    border: 1px solid #000000;
                    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
                }
            """)
            self.btn_save.setStyleSheet("""
                QPushButton {
                    background-color: #000000;
                    color: #FFFFFF;
                    font-weight: 600;
                    padding: 6px 18px;
                    border-radius: 6px;
                    border: none;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #2C2C2E;
                }
            """)
            self.btn_lang.setStyleSheet("""
                QPushButton {
                    background-color: #E2E2E8;
                    color: #000000;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 13px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #D6D6DC;
                }
            """)

    def _save_settings(self):
        self.config["hotkey_main"] = getattr(self, "val_hotkey_main", self.config["hotkey_main"])
        self.config["hotkey_alt"] = getattr(self, "val_hotkey_alt", self.config["hotkey_alt"])
        self.config["hotkey_history"] = getattr(self, "val_hotkey_history", self.config["hotkey_history"])

        self.config["enter_after_insert"] = self.chk_enter.isChecked()
        self.config["paste_suffix"] = self.combo_suffix.currentData()
        self.config["microphone_device"] = self.combo_mic.currentData()
        self.config["export_folder"] = self.txt_export_folder.text()

        self.config["whisper_model"] = self.combo_model.currentData()
        self.config["dictation_language"] = self.combo_dict_lang.currentData()

        self.config["capsule_size"] = self.combo_size.currentData()
        self.config["capsule_theme"] = self.combo_theme.currentData()

        self.config["ai_cleanup_enabled"] = self.chk_ai.isChecked()
        self.config["ai_base_url"] = self.txt_ai_url.text().strip()
        self.config["ai_model"] = self.txt_ai_model.text().strip()

        key_plain = self.txt_ai_key.text().strip()
        if key_plain:
            self.config["ai_api_key_encrypted"] = encrypt_secret(key_plain)
        else:
            self.config["ai_api_key_encrypted"] = ""

        self.config.save()
        self.settings_saved.emit()
        self.close()
