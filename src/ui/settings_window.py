"""
Settings & Control Panel for Dictatly Windows.
Configuration for hotkeys, text injection behavior, audio input devices,
Faster-Whisper model selection, floating HUD, and optional AI text cleanup.
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
    QFileDialog, QPlainTextEdit
)

from ..localization import t
from ..config import AppConfig, get_resource_dir
from ..core.hotkey import GlobalHotkeyManager
from ..core.audio import AudioRecorder
from ..core.security import encrypt_secret, decrypt_secret
from ..core.autostart import is_autostart_enabled, set_autostart, create_shortcuts
from ..engine.ai_cleaner import AICleaner
from .hud import CapsulePreviewCanvas, HUDState
from .icons import get_svg_icon

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
    """Grouped card container with standard rounded borders."""
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

class MicLevelMeter(QWidget):
    """Sleek real-time audio volume VU-meter bar with smooth decay."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(10)
        self.setMinimumWidth(180)
        self._target_level: float = 0.0
        self._current_level: float = 0.0
        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(25)
        self._decay_timer.timeout.connect(self._step_decay)

    def set_level(self, level: float):
        level = max(0.0, min(1.0, float(level)))
        if level > self._target_level:
            self._target_level = level
            self._current_level = max(self._current_level, level * 0.85)
        else:
            self._target_level = level
        if not self._decay_timer.isActive():
            self._decay_timer.start()
        self.update()

    def reset(self):
        self._target_level = 0.0
        self._current_level = 0.0
        self._decay_timer.stop()
        self.update()

    def _step_decay(self):
        if self._current_level < self._target_level:
            self._current_level += (self._target_level - self._current_level) * 0.5
        else:
            self._current_level += (self._target_level - self._current_level) * 0.18
        if self._current_level < 0.01 and self._target_level < 0.01:
            self._current_level = 0.0
            self._decay_timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = h / 2.0

        # Background track
        track_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius, radius)
        painter.fillPath(track_path, QBrush(QColor(36, 36, 40)))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        painter.drawPath(track_path)

        # Active level fill
        fill_w = max(0.0, (w - 2.0) * self._current_level)
        if fill_w > 2.0:
            fill_rect = QRectF(1.0, 1.0, fill_w, h - 2.0)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, radius - 0.5, radius - 0.5)

            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor(48, 209, 88))
            grad.setColorAt(0.7, QColor(255, 214, 10))
            grad.setColorAt(0.9, QColor(255, 159, 10))
            grad.setColorAt(1.0, QColor(255, 69, 58))

            painter.fillPath(fill_path, QBrush(grad))

class SettingsWindow(QWidget):
    settings_saved = Signal()
    restart_service_requested = Signal()
    preview_hud_requested = Signal(str)
    mic_level_signal = Signal(float)

    def __init__(self, config: AppConfig, hotkey_mgr: GlobalHotkeyManager):
        super().__init__()
        self.config = config
        self.hotkey_mgr = hotkey_mgr
        self.current_recording_target = None
        self._mic_test_stream = None
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Set Window Icon
        res_dir = get_resource_dir()
        icon_path = res_dir / "app_icon_64.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setMinimumSize(540, 680)
        self.resize(560, 710)

        self._init_ui()
        self.mic_level_signal.connect(self.meter_mic.set_level)
        self.combo_mic.currentIndexChanged.connect(lambda: self._start_mic_test_stream() if self.isVisible() else None)
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

        # === Card 2: Режим записи и поведение (Behavior & Mode) ===
        self.hdr_behavior = self._create_section_header("")
        body_layout.addWidget(self.hdr_behavior)

        self.card_behavior = SettingsCard(theme)
        card_b_layout = QVBoxLayout(self.card_behavior)
        card_b_layout.setContentsMargins(16, 12, 16, 12)
        card_b_layout.setSpacing(10)

        # Recording Mode (Toggle vs Push-to-Talk)
        mode_row = QHBoxLayout()
        self.lbl_rec_mode = QLabel()
        self.combo_rec_mode = QComboBox()
        self.combo_rec_mode.setMaximumWidth(190)
        self.combo_rec_mode.addItem("", "toggle")
        self.combo_rec_mode.addItem("", "push_to_talk")
        rm_idx = self.combo_rec_mode.findData(self.config.get("recording_mode", "toggle"))
        if rm_idx >= 0:
            self.combo_rec_mode.setCurrentIndex(rm_idx)
        mode_row.addWidget(self.lbl_rec_mode)
        mode_row.addStretch()
        mode_row.addWidget(self.combo_rec_mode)
        card_b_layout.addLayout(mode_row)
        card_b_layout.addWidget(self._create_divider(theme))

        # Audio Feedback
        self.chk_sound = QCheckBox()
        self.chk_sound.setChecked(self.config.get("sound_effects_enabled", True))
        card_b_layout.addWidget(self.chk_sound)
        card_b_layout.addWidget(self._create_divider(theme))

        # Smart Punctuation
        self.chk_smart_punct = QCheckBox()
        self.chk_smart_punct.setChecked(self.config.get("smart_punctuation_enabled", True))
        card_b_layout.addWidget(self.chk_smart_punct)
        card_b_layout.addWidget(self._create_divider(theme))

        # Silence Auto-Stop Timeout
        silence_row = QHBoxLayout()
        self.lbl_silence = QLabel()
        self.combo_silence = QComboBox()
        self.combo_silence.setMaximumWidth(190)
        self.combo_silence.addItem("", 0)
        self.combo_silence.addItem("", 10)
        self.combo_silence.addItem("", 15)
        self.combo_silence.addItem("", 30)
        s_idx = self.combo_silence.findData(self.config.get("silence_timeout_seconds", 15))
        if s_idx >= 0:
            self.combo_silence.setCurrentIndex(s_idx)
        silence_row.addWidget(self.lbl_silence)
        silence_row.addStretch()
        silence_row.addWidget(self.combo_silence)
        card_b_layout.addLayout(silence_row)
        card_b_layout.addWidget(self._create_divider(theme))

        # Enter after insert
        self.chk_enter = QCheckBox()
        self.chk_enter.setChecked(self.config["enter_after_insert"])
        card_b_layout.addWidget(self.chk_enter)
        card_b_layout.addWidget(self._create_divider(theme))

        # Suffix
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

        # === Card: Словарь автозамен (Vocabulary) ===
        self.hdr_vocab = self._create_section_header("")
        body_layout.addWidget(self.hdr_vocab)

        self.card_vocab = SettingsCard(theme)
        card_v_layout = QVBoxLayout(self.card_vocab)
        card_v_layout.setContentsMargins(16, 12, 16, 12)
        card_v_layout.setSpacing(6)

        self.hint_vocab = QLabel()
        self.hint_vocab.setStyleSheet("color: #86868B; font-size: 11px;")
        card_v_layout.addWidget(self.hint_vocab)

        self.txt_vocab = QPlainTextEdit()
        self.txt_vocab.setFixedHeight(90)
        self.txt_vocab.setPlaceholderText("гитхаб = GitHub\nпайтон = Python\nдокер = Docker")
        repls = self.config.get("custom_replacements", {})
        lines = [f"{k} = {v}" for k, v in repls.items()]
        self.txt_vocab.setPlainText("\n".join(lines))
        card_v_layout.addWidget(self.txt_vocab)
        body_layout.addWidget(self.card_vocab)

        # === Card: Система и запуск (System & Launch) ===
        self.hdr_system = self._create_section_header("")
        body_layout.addWidget(self.hdr_system)

        self.card_system = SettingsCard(theme)
        card_sys_layout = QVBoxLayout(self.card_system)
        card_sys_layout.setContentsMargins(16, 12, 16, 12)
        card_sys_layout.setSpacing(10)

        # Autostart checkbox & hint
        autostart_vbox = QVBoxLayout()
        autostart_vbox.setSpacing(3)
        self.chk_autostart = QCheckBox()
        self.chk_autostart.setChecked(is_autostart_enabled())
        self.chk_autostart.toggled.connect(self._on_autostart_toggled)
        autostart_vbox.addWidget(self.chk_autostart)
        self.hint_autostart = QLabel()
        self.hint_autostart.setStyleSheet("color: #86868B; font-size: 11px; margin-left: 24px;")
        autostart_vbox.addWidget(self.hint_autostart)
        card_sys_layout.addLayout(autostart_vbox)

        card_sys_layout.addWidget(self._create_divider(theme))

        # Shortcuts row
        shortcuts_row = QHBoxLayout()
        shortcuts_vbox = QVBoxLayout()
        shortcuts_vbox.setSpacing(3)
        self.lbl_shortcuts = QLabel()
        self.lbl_shortcuts.setStyleSheet("font-size: 13px; font-weight: 500;")
        self.hint_shortcuts = QLabel()
        self.hint_shortcuts.setStyleSheet("color: #86868B; font-size: 11px;")
        shortcuts_vbox.addWidget(self.lbl_shortcuts)
        shortcuts_vbox.addWidget(self.hint_shortcuts)
        shortcuts_row.addLayout(shortcuts_vbox, 1)

        self.btn_shortcuts = QPushButton()
        self.btn_shortcuts.setFixedWidth(140)
        self.btn_shortcuts.clicked.connect(self._create_app_shortcuts)
        shortcuts_row.addWidget(self.btn_shortcuts)
        card_sys_layout.addLayout(shortcuts_row)

        body_layout.addWidget(self.card_system)

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
        cur_dev = self.config.get("microphone_device")
        saved_name = (self.config.get("microphone_device_name") or "").strip().lower()
        if not saved_name and cur_dev is not None:
            try:
                import sounddevice as sd
                saved_name = sd.query_devices(cur_dev).get("name", "").strip().lower()
            except Exception:
                saved_name = ""

        # Match current device by index or fallback to name matching (for device migrations)
        matched = False
        for d in devices:
            clean_name = d["name"].replace("\r", " ").replace("\n", " ").strip()
            display_name = clean_name if len(clean_name) <= 40 else clean_name[:37] + "..."
            self.combo_mic.addItem(display_name, d["index"])
            if not matched:
                if cur_dev is not None and cur_dev == d["index"]:
                    self.combo_mic.setCurrentIndex(self.combo_mic.count() - 1)
                    matched = True
                elif saved_name and saved_name in d["name"].strip().lower():
                    self.combo_mic.setCurrentIndex(self.combo_mic.count() - 1)
                    matched = True
        mic_row.addWidget(self.lbl_mic)
        mic_row.addStretch()
        mic_row.addWidget(self.combo_mic)
        card_a_layout.addLayout(mic_row)

        meter_row = QHBoxLayout()
        meter_row.setContentsMargins(0, 2, 0, 2)
        self.lbl_mic_test = QLabel()
        self.lbl_mic_test.setStyleSheet("color: #86868B; font-size: 11px;")
        self.meter_mic = MicLevelMeter()
        meter_row.addWidget(self.lbl_mic_test)
        meter_row.addSpacing(6)
        meter_row.addWidget(self.meter_mic, 1)
        card_a_layout.addLayout(meter_row)

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
        card_hud_layout = QVBoxLayout(self.card_hud)
        card_hud_layout.setContentsMargins(16, 12, 16, 12)
        card_hud_layout.setSpacing(10)

        # Top row: Size label, ComboBox, and Test Button
        size_row = QHBoxLayout()
        self.lbl_size = QLabel()
        self.lbl_size.setStyleSheet("font-size: 13px; font-weight: 500;")

        self.combo_size = QComboBox()
        self.combo_size.setMinimumWidth(185)
        self.combo_size.addItem("", "small")
        self.combo_size.addItem("", "medium")
        self.combo_size.addItem("", "large")
        sidx = self.combo_size.findData(self.config["capsule_size"])
        if sidx >= 0:
            self.combo_size.setCurrentIndex(sidx)
        self.combo_size.currentIndexChanged.connect(self._on_size_changed)

        self.btn_test_hud = QPushButton()
        self.btn_test_hud.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 5px 12px;
                color: #F5F5F7;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_test_hud.clicked.connect(self._on_test_hud_clicked)

        size_row.addWidget(self.lbl_size)
        size_row.addWidget(self.combo_size)
        size_row.addStretch()
        size_row.addWidget(self.btn_test_hud)
        card_hud_layout.addLayout(size_row)

        card_hud_layout.addWidget(self._create_divider(theme))

        # Bottom row: Live animated preview canvas
        preview_container = QFrame()
        preview_container.setStyleSheet("""
            QFrame {
                background-color: #1A1A1D;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(6, 6, 6, 6)

        cur_size = self.config.get("capsule_size", "medium")
        self.preview_canvas = CapsulePreviewCanvas(size_mode=cur_size)
        preview_layout.addWidget(self.preview_canvas)
        card_hud_layout.addWidget(preview_container)

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
        self.btn_restart.setMinimumWidth(165)
        self.btn_restart.clicked.connect(self._on_restart_clicked)
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

        # Behavior & Mode
        self.hdr_behavior.setText(t("behavior_section", lang))
        self.lbl_rec_mode.setText(t("recording_mode", lang) + ":")
        self.combo_rec_mode.setItemText(0, t("mode_toggle", lang))
        self.combo_rec_mode.setItemText(1, t("mode_push_to_talk", lang))
        self.chk_sound.setText(t("sound_effects", lang))
        self.chk_smart_punct.setText(t("smart_punctuation", lang))
        self.lbl_silence.setText(t("silence_timeout", lang) + ":")
        self.combo_silence.setItemText(0, t("timeout_disabled", lang))
        self.combo_silence.setItemText(1, t("timeout_10s", lang))
        self.combo_silence.setItemText(2, t("timeout_15s", lang))
        self.combo_silence.setItemText(3, t("timeout_30s", lang))
        self.chk_enter.setText(t("enter_after_insert", lang))
        self.lbl_suffix.setText(t("paste_suffix", lang) + ":")
        self.combo_suffix.setItemText(0, t("suffix_space", lang))
        self.combo_suffix.setItemText(1, t("suffix_none", lang))
        self.combo_suffix.setItemText(2, t("suffix_newline", lang))

        # Vocabulary
        self.hdr_vocab.setText(t("vocabulary_section", lang))
        self.hint_vocab.setText(t("vocabulary_hint", lang))
        if lang == "ru":
            self.txt_vocab.setPlaceholderText("гитхаб = GitHub\nпайтон = Python\nдокер = Docker")
        else:
            self.txt_vocab.setPlaceholderText("github = GitHub\npython = Python\ndocker = Docker")

        # System & Launch
        self.hdr_system.setText(t("system_section", lang))
        self.chk_autostart.setText(t("autostart_with_windows", lang))
        self.hint_autostart.setText(t("autostart_with_windows_hint", lang))
        self.lbl_shortcuts.setText(t("create_shortcuts", lang))
        self.hint_shortcuts.setText(t("create_shortcuts_hint", lang))
        self.btn_shortcuts.setText(t("create_shortcuts", lang))

        # Audio
        self.lbl_mic.setText(t("microphone_select", lang) + ":")
        self.lbl_mic_test.setText(t("mic_test_label", lang))
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
        self.hdr_hud.setText(t("hud_section", lang))
        self.lbl_size.setText(t("capsule_size", lang) + ":")
        if lang == "ru":
            self.combo_size.setItemText(0, "Компактный (74×32)")
            self.combo_size.setItemText(1, "Стандартный (96×40)")
            self.combo_size.setItemText(2, "Крупный (124×48)")
            self.btn_test_hud.setText("Показать на экране")
        else:
            self.combo_size.setItemText(0, "Compact (74×32)")
            self.combo_size.setItemText(1, "Standard (96×40)")
            self.combo_size.setItemText(2, "Large (124×48)")
            self.btn_test_hud.setText("Show on Screen")

        # AI
        self.lbl_ai_desc.setText(t("ai_cleanup_desc", lang))
        self.chk_ai.setText(t("enable_ai_cleanup", lang))
        self.lbl_ai_url.setText(t("api_base_url", lang) + ":")
        self.lbl_ai_model.setText(t("api_model", lang) + ":")
        self.lbl_ai_key.setText(t("api_key", lang) + ":")
        self.btn_test_conn.setText(t("test_connection", lang))

        # Footer
        if self.btn_restart.isEnabled():
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
            self.lbl_conn_status.setText(t('connection_ok', lang))
            self.lbl_conn_status.setStyleSheet("color: #34C759; font-weight: 500;")
        else:
            self.lbl_conn_status.setText(f"{t('connection_failed', lang)}: {msg}")
            self.lbl_conn_status.setStyleSheet("color: #FF453A;")

    def _on_restart_clicked(self):
        self.btn_restart.setEnabled(False)
        lang = self.config["interface_language"]
        self.btn_restart.setText(t("restarting_service", lang))
        self.btn_restart.setIcon(QIcon())
        self.restart_service_requested.emit()

    def notify_service_restarted(self, success: bool = True, message: str = ""):
        lang = self.config["interface_language"]
        theme = self.config["capsule_theme"]
        if success:
            self.btn_restart.setIcon(get_svg_icon("check", 14, "#34C759"))
            self.btn_restart.setText(t('service_restarted', lang))
            if theme == "dark":
                self.btn_restart.setStyleSheet("""
                    QPushButton {
                        background-color: #1A3322;
                        border: 1px solid #34C759;
                        color: #34C759;
                        font-weight: 500;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 13px;
                    }
                """)
            else:
                self.btn_restart.setStyleSheet("""
                    QPushButton {
                        background-color: #E8F8ED;
                        border: 1px solid #34C759;
                        color: #248A3D;
                        font-weight: 500;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 13px;
                    }
                """)
        else:
            self.btn_restart.setIcon(get_svg_icon("close", 14, "#FF453A"))
            self.btn_restart.setText(t('connection_failed', lang))
            self.btn_restart.setStyleSheet("""
                QPushButton {
                    background-color: #3A1E1E;
                    border: 1px solid #FF453A;
                    color: #FF453A;
                    font-weight: 500;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 13px;
                }
            """)

        def revert():
            self.btn_restart.setEnabled(True)
            self.btn_restart.setIcon(QIcon())
            self.btn_restart.setStyleSheet("")
            self.btn_restart.setText(t("restart_service", self.config["interface_language"]))

        QTimer.singleShot(2500, revert)

    def _on_autostart_toggled(self, checked: bool):
        set_autostart(checked)
        self.config["autostart_with_windows"] = checked
        self.config.save()

    def _create_app_shortcuts(self):
        create_shortcuts(desktop=True, start_menu=True)
        lang = self.config["interface_language"]
        self.btn_shortcuts.setIcon(get_svg_icon("check", 14, "#34C759"))
        self.btn_shortcuts.setText(t('shortcuts_created', lang))
        def revert_shortcuts():
            self.btn_shortcuts.setIcon(QIcon())
            self.btn_shortcuts.setText(t("create_shortcuts", self.config["interface_language"]))
        QTimer.singleShot(2500, revert_shortcuts)

    def _toggle_language(self):
        new_lang = "en" if self.config["interface_language"] == "ru" else "ru"
        self.config["interface_language"] = new_lang
        self.config.save()
        self.retranslate_ui()

    def _on_size_changed(self, idx: int):
        size = self.combo_size.currentData()
        self.preview_canvas.set_size_mode(size)

    def _on_test_hud_clicked(self):
        size = self.combo_size.currentData()
        self.preview_hud_requested.emit(size)

    def _apply_global_theme(self, theme: str = "dark"):
        check_icon_path = str(get_resource_dir() / "check_white.png").replace("\\", "/")
        self.setStyleSheet(f"""
            SettingsWindow, QScrollArea, #BodyWidget {{
                background-color: #1E1E20;
                color: #F5F5F7;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", sans-serif;
            }}
            #HeaderFrame {{
                background-color: #242426;
                border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            }}
            #FooterFrame {{
                background-color: #242426;
                border-top: 1px solid rgba(255, 255, 255, 0.07);
            }}
            QLabel {{
                color: #F5F5F7;
                font-size: 13px;
            }}
            QLineEdit, QComboBox, QPlainTextEdit {{
                background-color: #28282A;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 8px;
                color: #F5F5F7;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{
                border: 1px solid #FFFFFF;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QPushButton {{
                background-color: #323236;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 12px;
                color: #F5F5F7;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #3C3C40;
            }}
            QCheckBox {{
                color: #F5F5F7;
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                background-color: #1A1A1D;
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid rgba(255, 255, 255, 0.45);
            }}
            QCheckBox::indicator:checked {{
                background-color: #0A84FF;
                border: 1px solid #0A84FF;
                image: url("{check_icon_path}");
            }}
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

    def _save_settings(self):
        self.config["hotkey_main"] = getattr(self, "val_hotkey_main", self.config["hotkey_main"])
        self.config["hotkey_alt"] = getattr(self, "val_hotkey_alt", self.config["hotkey_alt"])
        self.config["hotkey_history"] = getattr(self, "val_hotkey_history", self.config["hotkey_history"])

        # Recording Mode & Processing
        self.config["recording_mode"] = self.combo_rec_mode.currentData()
        self.config["sound_effects_enabled"] = self.chk_sound.isChecked()
        self.config["smart_punctuation_enabled"] = self.chk_smart_punct.isChecked()
        self.config["silence_timeout_seconds"] = self.combo_silence.currentData()

        # Vocabulary Replacements
        vocab_dict = {}
        for line in self.txt_vocab.toPlainText().splitlines():
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() and v.strip():
                    vocab_dict[k.strip()] = v.strip()
        self.config["custom_replacements"] = vocab_dict

        self.config["enter_after_insert"] = self.chk_enter.isChecked()
        self.config["autostart_with_windows"] = self.chk_autostart.isChecked()
        set_autostart(self.chk_autostart.isChecked())
        self.config["paste_suffix"] = self.combo_suffix.currentData()
        selected_mic = self.combo_mic.currentData()
        self.config["microphone_device"] = selected_mic
        if selected_mic is not None:
            try:
                import sounddevice as sd
                dev_info = sd.query_devices(selected_mic)
                self.config["microphone_device_name"] = dev_info.get("name", "").strip()
            except Exception:
                self.config["microphone_device_name"] = ""
        else:
            self.config["microphone_device_name"] = None
        self.config["export_folder"] = self.txt_export_folder.text()

        self.config["whisper_model"] = self.combo_model.currentData()
        self.config["dictation_language"] = self.combo_dict_lang.currentData()

        self.config["capsule_size"] = self.combo_size.currentData()
        self.config["capsule_theme"] = "dark"

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

    def _start_mic_test_stream(self):
        """Starts ephemeral sounddevice input stream to feed live mic level meter."""
        self._stop_mic_test_stream()
        dev_idx = self.combo_mic.currentData()
        try:
            import numpy as np
            import sounddevice as sd

            def audio_cb(indata, frames, time_info, status):
                try:
                    if indata.ndim > 1 and indata.shape[1] > 1:
                        mono = np.mean(indata, axis=1)
                    else:
                        mono = indata
                    rms = float(np.sqrt(np.mean(np.square(mono))))
                    vol = min(1.0, rms * 14.0)
                    self.mic_level_signal.emit(vol)
                except Exception:
                    pass

            extra_settings = AudioRecorder.get_extra_settings(dev_idx)
            stream = None
            # Probe supported rate and channels
            for ch in (1, 2):
                for rate in (16000, 48000, 44100):
                    try:
                        stream = sd.InputStream(
                            device=dev_idx,
                            channels=ch,
                            samplerate=rate,
                            blocksize=1024,
                            dtype="float32",
                            callback=audio_cb,
                            extra_settings=extra_settings
                        )
                        stream.start()
                        break
                    except Exception:
                        stream = None
                if stream is not None:
                    break

            self._mic_test_stream = stream
        except Exception as e:
            print(f"[Settings] Could not start mic test stream: {e}")
            self._mic_test_stream = None

    def _stop_mic_test_stream(self):
        """Stops mic test stream and resets VU meter."""
        if self._mic_test_stream is not None:
            try:
                self._mic_test_stream.stop()
                self._mic_test_stream.close()
            except Exception:
                pass
            self._mic_test_stream = None
        if hasattr(self, "meter_mic"):
            self.meter_mic.reset()

    def showEvent(self, event):
        super().showEvent(event)
        self._start_mic_test_stream()

    def hideEvent(self, event):
        self._stop_mic_test_stream()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._stop_mic_test_stream()
        super().closeEvent(event)

