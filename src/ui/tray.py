"""
System Tray Integration for Dictatly Windows.
Provides tray icon, status notifications, and quick action context menu.
"""

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from ..localization import t
from ..config import AppConfig

def create_tray_icon(is_active: bool = True) -> QIcon:
    """Renders crisp High-DPI 64x64 monochrome microphone icon in Apple minimalist style."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2.0)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Base microphone shape
    mic_color = QColor(245, 245, 247) if is_active else QColor(142, 142, 147, 180)
    painter.setPen(Qt.NoPen)
    painter.setBrush(mic_color)

    # Mic capsule body
    painter.drawRoundedRect(11, 4, 10, 15, 5, 5)

    # Mic stand cradle arc
    painter.setPen(QPen(mic_color, 1.8))
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(7, 8, 18, 14, 0, -180 * 16)

    # Stand vertical pole and base
    painter.drawLine(16, 22, 16, 27)
    painter.drawLine(10, 27, 22, 27)

    # Subtle discreet status indicator when active
    if is_active:
        painter.setPen(QPen(QColor(12, 12, 14), 1.0))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(22, 20, 5, 5)

    painter.end()
    return QIcon(pixmap)

class SystemTrayManager(QObject):
    open_settings_requested = Signal()
    open_history_requested = Signal()
    toggle_dictation_requested = Signal()
    toggle_pause_requested = Signal(bool)
    exit_requested = Signal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(create_tray_icon(True))
        self.tray.setToolTip(t("app_name", self.config["interface_language"]))

        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #161618;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QMenu::item:disabled {
                color: #8E8E93;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }
        """)
        self._build_menu()

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _build_menu(self):
        lang = self.config["interface_language"]
        was_paused = self.act_pause.isChecked() if hasattr(self, "act_pause") else False
        self.menu.clear()

        # Title (disabled)
        title_action = self.menu.addAction(t("app_name", lang))
        title_action.setEnabled(False)
        self.menu.addSeparator()

        # Open Settings
        act_settings = self.menu.addAction(t("tray_open_settings", lang))
        act_settings.triggered.connect(self.open_settings_requested.emit)

        # Open Quick History
        act_history = self.menu.addAction(t("tray_open_history", lang))
        act_history.triggered.connect(self.open_history_requested.emit)

        self.menu.addSeparator()

        # Pause Global Hotkeys (Gaming / Calls)
        self.act_pause = self.menu.addAction(t("tray_pause_hotkeys", lang))
        self.act_pause.setCheckable(True)
        self.act_pause.setChecked(was_paused)
        self.act_pause.toggled.connect(self.toggle_pause_requested.emit)

        # Toggle Dictation
        act_toggle = self.menu.addAction(t("tray_toggle_dictation", lang))
        act_toggle.triggered.connect(self.toggle_dictation_requested.emit)

        self.menu.addSeparator()

        # Exit
        act_exit = self.menu.addAction(t("tray_exit", lang))
        act_exit.triggered.connect(self.exit_requested.emit)

    def set_paused(self, paused: bool):
        if hasattr(self, "act_pause"):
            self.act_pause.blockSignals(True)
            self.act_pause.setChecked(paused)
            self.act_pause.blockSignals(False)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.open_settings_requested.emit()

    def update_language(self):
        self._build_menu()
        self.tray.setToolTip(t("app_name", self.config["interface_language"]))

    def show_notification(self, title: str, message: str):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 2500)
