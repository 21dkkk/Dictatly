"""
High-End Quick History Window & Audio Batch Transcription for Dictatly Windows.
Features:
- Sleek transcript cards with relative time formatting, word count & duration badges
- Drag & Drop audio zone with drag-over visual feedback
- Animated progress bar and one-click copy with feedback
- Ultra-lightweight native PySide6 styling
"""

import datetime
from pathlib import Path
from typing import Optional, List
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QPainter, QBrush, QPen, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QProgressBar, QApplication
)
from ..localization import t
from ..core.database import HistoryDatabase, PAGE_SIZE
from ..config import AppConfig

def format_relative_time(iso_time_str: str) -> str:
    """Converts ISO timestamp into human relative string ('Только что', '5 мин назад', etc.)."""
    try:
        dt = datetime.datetime.fromisoformat(iso_time_str)
        now = datetime.datetime.now()
        diff = now - dt

        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Только что"
        elif seconds < 3600:
            mins = seconds // 60
            return f"{mins} мин назад"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} ч назад"
        else:
            return dt.strftime("%d.%m %H:%M")
    except Exception:
        return iso_time_str.replace("T", " ")[:16]

class TranscriptCard(QFrame):
    clicked = Signal(str)

    def __init__(self, text: str, created_at: str, duration: float, word_count: int, source: str = "mic", theme: str = "dark"):
        super().__init__()
        self.text = text
        self.theme = theme
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("TranscriptCard")
        self.setToolTip("Нажмите для копирования / Click to copy")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header Row: Time + Minimalist Metadata
        header = QHBoxLayout()
        header.setSpacing(8)

        rel_time = format_relative_time(created_at)
        time_label = QLabel(rel_time)
        time_label.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: 600;")
        header.addWidget(time_label)

        header.addStretch()

        meta_parts = []
        if duration > 0:
            meta_parts.append(f"{duration:.1f}с")
        if word_count > 0:
            meta_parts.append(f"{word_count} сл.")
        if source != "mic":
            meta_parts.append("Файл")

        if meta_parts:
            meta_label = QLabel("  •  ".join(meta_parts))
            meta_label.setStyleSheet("color: #8E8E93; font-size: 11px;")
            header.addWidget(meta_label)

        layout.addLayout(header)

        # Content Text
        content_label = QLabel(text)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                line-height: 1.4;
                color: #FFFFFF;
            }
        """ if theme == "dark" else """
            QLabel {
                font-size: 13px;
                line-height: 1.4;
                color: #000000;
            }
        """)
        layout.addWidget(content_label)

        # Apple Card Styling
        if theme == "dark":
            self.setStyleSheet("""
                #TranscriptCard {
                    background-color: #28282A;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }
                #TranscriptCard:hover {
                    background-color: #323236;
                    border: 1px solid rgba(255, 255, 255, 0.14);
                }
            """)
        else:
            self.setStyleSheet("""
                #TranscriptCard {
                    background-color: #FFFFFF;
                    border: 1px solid rgba(0, 0, 0, 0.07);
                    border-radius: 10px;
                }
                #TranscriptCard:hover {
                    background-color: #F5F5F7;
                    border: 1px solid rgba(0, 0, 0, 0.12);
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.text)

class DropZoneWidget(QFrame):
    """Minimalist Drag & Drop Zone in Apple aesthetic."""
    def __init__(self, theme: str = "dark", lang: str = "ru"):
        super().__init__()
        self.theme = theme
        self.lang = lang
        self.is_drag_over = False
        self.setObjectName("DropZone")
        self.setFixedHeight(60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        hint = t("batch_import_hint", lang)
        sub = "Автоматическая транскрипция и экспорт в .txt" if lang == "ru" else "Automatic transcription and export to .txt"
        self.lbl_icon = QLabel(hint)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 12px; font-weight: 600; color: #FFFFFF;" if theme == "dark" else "font-size: 12px; font-weight: 600; color: #000000;")

        self.lbl_sub = QLabel(sub)
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #8E8E93;")

        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_sub)
        self._update_style()

    def set_text(self, title: str, subtitle: Optional[str] = None):
        """Update drop zone display text."""
        self.lbl_icon.setText(title)
        if subtitle is not None:
            self.lbl_sub.setText(subtitle)
            self.lbl_sub.setVisible(bool(subtitle))

    def setText(self, text: str):
        """Compatibility setter for single text string."""
        self.set_text(text)

    def set_drag_over(self, active: bool):
        self.is_drag_over = active
        self._update_style()

    def _update_style(self):
        if self.is_drag_over:
            border_color = "rgba(255, 255, 255, 0.4)" if self.theme == "dark" else "rgba(0, 0, 0, 0.4)"
            bg_color = "rgba(255, 255, 255, 0.05)" if self.theme == "dark" else "rgba(0, 0, 0, 0.03)"
        else:
            border_color = "rgba(255, 255, 255, 0.12)" if self.theme == "dark" else "rgba(0, 0, 0, 0.12)"
            bg_color = "transparent"

        self.setStyleSheet(f"""
            #DropZone {{
                border: 1px dashed {border_color};
                background-color: {bg_color};
                border-radius: 10px;
            }}
        """)

class QuickHistoryWindow(QWidget):
    batch_transcribe_requested = Signal(list)

    def __init__(self, db: HistoryDatabase, config: AppConfig):
        super().__init__()
        self.db = db
        self.config = config
        self.current_page = 1
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        lang = self.config["interface_language"]
        self.setWindowTitle(t("history_title", lang))

        # Set Window Icon
        res_dir = Path(__file__).resolve().parent.parent.parent / "resources"
        icon_path = res_dir / "app_icon_64.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setMinimumSize(480, 580)
        self.resize(500, 620)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        self._init_ui()
        self.refresh_list()

    def _init_ui(self):
        lang = self.config["interface_language"]
        theme = self.config["capsule_theme"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header Title
        header = QHBoxLayout()
        title = QLabel(t("history_title", lang))
        title_color = "#FFFFFF" if theme == "dark" else "#000000"
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; letter-spacing: 0.3px; color: {title_color};")
        header.addWidget(title)
        header.addStretch()

        # Close button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.hide)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #8E8E93;
                border: none;
                border-radius: 13px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
                color: #FFFFFF;
            }
        """ if theme == "dark" else """
            QPushButton {
                background-color: rgba(0, 0, 0, 0.05);
                color: #8E8E93;
                border: none;
                border-radius: 13px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.10);
                color: #000000;
            }
        """)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # Productivity Stats
        self.lbl_stats = QLabel()
        self.lbl_stats.setStyleSheet("""
            QLabel {
                background-color: #242428;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 12px;
                color: #A1A1A6;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.lbl_stats)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по расшифровкам...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 14px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background-color: #1A1A1D;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.35);
                background-color: #202024;
            }
        """ if theme == "dark" else """
            QLineEdit {
                padding: 8px 14px;
                border-radius: 8px;
                border: 1px solid rgba(0, 0, 0, 0.14);
                background-color: #FFFFFF;
                color: #000000;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #000000;
            }
        """)
        layout.addWidget(self.search_input)

        # Cards Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_container.setAttribute(Qt.WA_StyledBackground, True)
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, 1)

        # Drag & Drop Zone
        self.drop_zone = DropZoneWidget(theme=theme, lang=lang)
        layout.addWidget(self.drop_zone)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: rgba(255, 255, 255, 0.08);
            }
            QProgressBar::chunk {
                background-color: #FFFFFF;
                border-radius: 2px;
            }
        """ if theme == "dark" else """
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: rgba(0, 0, 0, 0.06);
            }
            QProgressBar::chunk {
                background-color: #000000;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Pagination controls
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("‹")
        self.btn_prev.setFixedSize(32, 26)
        self.btn_prev.clicked.connect(self._prev_page)

        self.page_label = QLabel("")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #8E8E93; font-size: 12px; font-weight: 500;")

        self.btn_next = QPushButton("›")
        self.btn_next.setFixedSize(32, 26)
        self.btn_next.clicked.connect(self._next_page)

        nav_btn_style = """
            QPushButton {
                background-color: #141416;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 15px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1E1E22;
                border: 1px solid rgba(255, 255, 255, 0.16);
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.04);
                background-color: #101012;
            }
        """ if theme == "dark" else """
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 6px;
                font-size: 15px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F2F2F7;
            }
            QPushButton:disabled {
                color: rgba(0, 0, 0, 0.2);
                border-color: rgba(0, 0, 0, 0.04);
            }
        """
        self.btn_prev.setStyleSheet(nav_btn_style)
        self.btn_next.setStyleSheet(nav_btn_style)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.page_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)

        # Global theme
        if theme == "dark":
            self.setStyleSheet("""
                QuickHistoryWindow {
                    background-color: #1E1E20;
                    color: #FFFFFF;
                }
            """)
        else:
            self.setStyleSheet("""
                QuickHistoryWindow {
                    background-color: #ECECEC;
                    color: #000000;
                }
            """)

    def _on_search_changed(self, text: str):
        self.current_page = 1
        self.refresh_list()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_list()

    def _next_page(self):
        total_items = self.db.get_total_count(self.search_input.text())
        total_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)
        if self.current_page < total_pages:
            self.current_page += 1
            self.refresh_list()

    def refresh_list(self):
        lang = self.config["interface_language"]
        theme = self.config["capsule_theme"]
        query = self.search_input.text()

        # Update productivity stats
        stats = self.db.get_today_stats()
        words = stats["words"]
        mins = stats["minutes_saved"]
        if words > 0:
            if lang == "ru":
                self.lbl_stats.setText(f"⚡ Сегодня: {words:,} слов  •  ~{mins:.1f} мин сэкономлено")
            else:
                self.lbl_stats.setText(f"⚡ Today: {words:,} words  •  ~{mins:.1f} min saved")
        else:
            if lang == "ru":
                self.lbl_stats.setText("⚡ Начните диктовку, чтобы отслеживать статистику за сегодня")
            else:
                self.lbl_stats.setText("⚡ Start dictating to track your productivity today")

        # Clear existing cards
        while self.cards_layout.count() > 1:
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        items = self.db.get_entries(page=self.current_page, page_size=PAGE_SIZE, search_query=query)
        total_count = self.db.get_total_count(search_query=query)
        total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

        if not items:
            empty_lbl = QLabel(t("history_empty", lang))
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #8E8E93; padding: 48px; font-size: 13px;")
            self.cards_layout.insertWidget(0, empty_lbl)
        else:
            for idx, row in enumerate(items):
                card = TranscriptCard(
                    text=row["text"],
                    created_at=row["created_at"],
                    duration=row["duration"],
                    word_count=row.get("word_count", len(row["text"].split())),
                    source=row.get("source", "mic"),
                    theme=theme
                )
                card.clicked.connect(self._copy_and_close)
                self.cards_layout.insertWidget(idx, card)

        self.page_label.setText(t("page_info", lang, current=self.current_page, total=total_pages))
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

    def _copy_and_close(self, text: str):
        QApplication.clipboard().setText(text)
        self.hide()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = Path(url.toLocalFile()).suffix.lower()
                if ext in (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"):
                    self.drop_zone.set_drag_over(True)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_zone.set_drag_over(False)

    def dropEvent(self, event: QDropEvent):
        self.drop_zone.set_drag_over(False)
        files = []
        for url in event.mimeData().urls():
            fpath = url.toLocalFile()
            ext = Path(fpath).suffix.lower()
            if ext in (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"):
                files.append(fpath)
        if files:
            self.batch_transcribe_requested.emit(files)
            event.acceptProposedAction()
