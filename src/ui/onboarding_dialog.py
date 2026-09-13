"""
First-Run Onboarding and Quick Setup Dialog for Dictatly.
Welcomes the user, explains key controls, and configures Windows Autostart and Desktop shortcuts.
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget
)

from ..localization import t
from ..config import AppConfig
from ..core.autostart import set_autostart, create_shortcuts

class CheckIndicator(QWidget):
    """Custom vector-rendered checkmark box with smooth anti-aliased rendering."""
    def __init__(self, checked: bool = True, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self._checked = checked
        self._theme = theme
        self._hover = False

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()

    def setTheme(self, theme: str):
        self._theme = theme
        self.update()

    def setHover(self, hover: bool):
        if self._hover != hover:
            self._hover = hover
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 6

        if self._checked:
            # Accent Blue checked background
            blue = QColor("#0A84FF") if self._theme == "dark" else QColor("#007AFF")
            painter.setBrush(blue)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

            # High-contrast white vector checkmark
            pen = QPen(QColor("#FFFFFF"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            w = rect.width()
            h = rect.height()
            x0 = rect.x()
            y0 = rect.y()
            path.moveTo(x0 + w * 0.25, y0 + h * 0.50)
            path.lineTo(x0 + w * 0.44, y0 + h * 0.69)
            path.lineTo(x0 + w * 0.75, y0 + h * 0.31)
            painter.drawPath(path)
        else:
            # Unchecked outline and background
            if self._theme == "dark":
                bg = QColor(255, 255, 255, 14 if self._hover else 8)
                border = QColor(255, 255, 255, 75 if self._hover else 40)
            else:
                bg = QColor(0, 0, 0, 10 if self._hover else 5)
                border = QColor(0, 0, 0, 80 if self._hover else 45)
            painter.setBrush(bg)
            painter.setPen(QPen(border, 1.4))
            painter.drawRoundedRect(rect, radius, radius)

class SetupOptionCard(QFrame):
    """Interactive card container for setup options with full-row clickability."""
    toggled = Signal(bool)

    def __init__(self, title: str, desc: str, checked: bool = True, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._checked = checked
        self._theme = theme
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("OptionCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(3)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setStyleSheet("color: #8E8E93; font-size: 11px;")
        self.lbl_desc.setWordWrap(True)
        text_vbox.addWidget(self.lbl_title)
        text_vbox.addWidget(self.lbl_desc)
        layout.addLayout(text_vbox, 1)

        self.indicator = CheckIndicator(checked=checked, theme=theme)
        layout.addWidget(self.indicator, 0, Qt.AlignVCenter)

        self._update_card_style(hover=False)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.indicator.setChecked(checked)
            self._update_card_style(hover=False)
            self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.indicator.setHover(True)
        self._update_card_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.indicator.setHover(False)
        self._update_card_style(hover=False)
        super().leaveEvent(event)

    def setTheme(self, theme: str):
        self._theme = theme
        self.indicator.setTheme(theme)
        self._update_card_style(hover=False)

    def _update_card_style(self, hover: bool):
        if self._theme == "dark":
            if hover:
                bg = "#2F2F32"
                border = "rgba(255, 255, 255, 0.18)"
            else:
                bg = "#252527"
                border = "rgba(255, 255, 255, 0.08)"
            self.setStyleSheet(f"""
                QFrame#OptionCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 9px;
                }}
            """)
        else:
            if hover:
                bg = "#F5F5F7"
                border = "rgba(0, 0, 0, 0.16)"
            else:
                bg = "#FFFFFF"
                border = "rgba(0, 0, 0, 0.08)"
            self.setStyleSheet(f"""
                QFrame#OptionCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 9px;
                }}
            """)

class OnboardingDialog(QDialog):
    completed = Signal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.setWindowTitle("Dictatly — Quick Setup")
        self.setFixedSize(510, 560)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        res_dir = Path(__file__).resolve().parent.parent.parent / "resources"
        ico_file = res_dir / "app_icon.ico"
        if not ico_file.exists():
            ico_file = res_dir / "app_icon_64.png"
        if ico_file.exists():
            self.setWindowIcon(QIcon(str(ico_file)))

        self._init_ui()
        self._apply_theme()

    def _init_ui(self):
        lang = self.config["interface_language"]
        theme = self.config["capsule_theme"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(16)

        # Header: App Icon + Title + Subtitle
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        icon_lbl = QLabel()
        res_dir = Path(__file__).resolve().parent.parent.parent / "resources"
        ico_file = res_dir / "app_icon_64.png"
        if ico_file.exists():
            pix = QPixmap(str(ico_file)).scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        header_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        lbl_title = QLabel(t("welcome_title", lang))
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        lbl_subtitle = QLabel(t("welcome_subtitle", lang))
        lbl_subtitle.setStyleSheet("color: #8E8E93; font-size: 12px;")
        lbl_subtitle.setWordWrap(True)
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_subtitle)
        header_layout.addLayout(title_vbox, 1)

        layout.addLayout(header_layout)

        # Instructions Card
        card = QFrame()
        card.setObjectName("SetupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        hdr_instructions = QLabel(t("onboarding_how_it_works", lang))
        hdr_instructions.setStyleSheet("font-size: 12px; font-weight: 600; color: #8E8E93; text-transform: uppercase; letter-spacing: 0.5px;")
        card_layout.addWidget(hdr_instructions)

        step1 = QLabel(f"• {t('onboarding_step1', lang)}")
        step1.setTextFormat(Qt.RichText)
        step1.setWordWrap(True)
        step1.setStyleSheet("font-size: 13px; line-height: 1.4;")
        card_layout.addWidget(step1)

        step2 = QLabel(f"• {t('onboarding_step2', lang)}")
        step2.setTextFormat(Qt.RichText)
        step2.setWordWrap(True)
        step2.setStyleSheet("font-size: 13px; line-height: 1.4;")
        card_layout.addWidget(step2)

        step3 = QLabel(f"• {t('onboarding_step3', lang)}")
        step3.setTextFormat(Qt.RichText)
        step3.setWordWrap(True)
        step3.setStyleSheet("font-size: 13px; line-height: 1.4;")
        card_layout.addWidget(step3)

        layout.addWidget(card)

        # Interactive Option Cards (Autostart & Shortcuts)
        options_vbox = QVBoxLayout()
        options_vbox.setSpacing(10)

        self.card_autostart = SetupOptionCard(
            title=t("onboarding_autostart_option", lang),
            desc=t("onboarding_autostart_desc", lang),
            checked=True,
            theme=theme
        )
        options_vbox.addWidget(self.card_autostart)

        self.card_shortcuts = SetupOptionCard(
            title=t("onboarding_shortcuts_option", lang),
            desc=t("onboarding_shortcuts_desc", lang),
            checked=True,
            theme=theme
        )
        options_vbox.addWidget(self.card_shortcuts)

        # Expose for API/test compatibility
        self.chk_autostart = self.card_autostart
        self.chk_shortcuts = self.card_shortcuts

        layout.addLayout(options_vbox)
        layout.addStretch()

        # Primary Action Button
        self.btn_start = QPushButton(t("onboarding_start_button", lang))
        self.btn_start.setFixedHeight(42)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setDefault(True)
        self.btn_start.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.btn_start)

    def _on_start_clicked(self):
        # 1. Windows Autostart
        enable_auto = self.card_autostart.isChecked()
        if enable_auto:
            set_autostart(True)
            self.config["autostart_with_windows"] = True
        else:
            set_autostart(False)
            self.config["autostart_with_windows"] = False

        # 2. Desktop and Start Menu shortcuts
        if self.card_shortcuts.isChecked():
            create_shortcuts(desktop=True, start_menu=True)

        # 3. Save first-run completed
        self.config["first_run_completed"] = True
        self.config.save()

        self.completed.emit()
        self.accept()

    def _apply_theme(self):
        theme = self.config["capsule_theme"]
        self.card_autostart.setTheme(theme)
        self.card_shortcuts.setTheme(theme)

        if theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #1E1E20;
                    color: #F5F5F7;
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", sans-serif;
                }
                #SetupCard {
                    background-color: #262628;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }
                QLabel {
                    color: #F5F5F7;
                }
                QPushButton {
                    background-color: #FFFFFF;
                    color: #000000;
                    font-size: 14px;
                    font-weight: 600;
                    border-radius: 8px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #E5E5EA;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ECECEC;
                    color: #1D1D1F;
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", sans-serif;
                }
                #SetupCard {
                    background-color: #FFFFFF;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 10px;
                }
                QLabel {
                    color: #1D1D1F;
                }
                QPushButton {
                    background-color: #000000;
                    color: #FFFFFF;
                    font-size: 14px;
                    font-weight: 600;
                    border-radius: 8px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2C2C2E;
                }
            """)
