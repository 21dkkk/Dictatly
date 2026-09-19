"""
History, analytics, and audio file import interface for Dictatly.
"""

import time
import math
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from PySide6.QtCore import Qt, Signal, QTimer, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QFont, QColor, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient, QPainterPath, QIcon, QMouseEvent
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QProgressBar, QApplication, QStackedWidget,
    QFileDialog
)

from ..localization import t
from ..core.database import HistoryDatabase, PAGE_SIZE
from ..config import AppConfig, get_resource_dir
from .icons import get_svg_pixmap, get_svg_icon


def get_ui_font(size: int = 10, weight: QFont.Weight = QFont.Normal) -> QFont:
    """Return application UI font."""
    font = QFont("Segoe UI", size)
    font.setStyleHint(QFont.SansSerif)
    font.setWeight(weight)
    return font


def format_relative_time(iso_time_str: str, lang: str = "ru") -> str:
    """Convert ISO timestamp into human-readable relative string."""
    try:
        dt = datetime.datetime.fromisoformat(iso_time_str)
        now = datetime.datetime.now()
        diff = now - dt

        seconds = int(diff.total_seconds())
        if seconds < 60:
            return t("time_just_now", lang)
        elif seconds < 3600:
            mins = seconds // 60
            return t("time_mins_ago", lang, mins=mins)
        elif seconds < 86400:
            hours = seconds // 3600
            return t("time_hours_ago", lang, hours=hours)
        elif seconds < 172800:
            return t("time_yesterday", lang, time=dt.strftime("%H:%M"))
        else:
            fmt = "%d.%m %H:%M" if lang == "ru" else "%b %d, %H:%M"
            return dt.strftime(fmt)
    except Exception:
        return iso_time_str.replace("T", " ")[:16]


class SlidingSegmentedControl(QWidget):
    """Segmented control with animated sliding selection pill."""
    segment_changed = Signal(int)

    def __init__(self, items: List[Tuple[str, str]], current_index: int = 0, parent=None):
        super().__init__(parent)
        self.items = items
        self.current_index = current_index
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)

        self._current_x = 3.0
        self._target_x = 3.0
        self._current_w = 100.0
        self._target_w = 100.0
        self._last_time = time.perf_counter()

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(4)
        self._anim_timer.timeout.connect(self._step_physics)

    def set_current_index(self, index: int):
        if 0 <= index < len(self.items):
            self.current_index = index
            self._update_targets()
            self.segment_changed.emit(index)

    def set_items(self, items: List[Tuple[str, str]]):
        self.items = items
        self._update_targets()
        self.update()

    def _update_targets(self):
        w = float(self.width())
        if not self.items or w <= 6:
            return
        pill_pad = 3.0
        slot_w = (w - (pill_pad * 2.0)) / float(len(self.items))
        self._target_x = pill_pad + (float(self.current_index) * slot_w)
        self._target_w = slot_w
        self._last_time = time.perf_counter()
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _step_physics(self):
        now = time.perf_counter()
        dt = max(0.001, min(0.05, now - self._last_time))
        self._last_time = now

        # Exponential spring smoothing
        speed = 22.0
        alpha = 1.0 - math.exp(-speed * dt)

        self._current_x += (self._target_x - self._current_x) * alpha
        self._current_w += (self._target_w - self._current_w) * alpha

        dist = abs(self._target_x - self._current_x) + abs(self._target_w - self._current_w)
        if dist < 0.2:
            self._current_x = self._target_x
            self._current_w = self._target_w
            self._anim_timer.stop()

        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_targets()
        self._current_x = self._target_x
        self._current_w = self._target_w

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            w = float(self.width())
            if len(self.items) > 0 and w > 6:
                slot_w = (w - 6.0) / float(len(self.items))
                idx = int((event.position().x() - 3.0) / slot_w)
                idx = max(0, min(len(self.items) - 1, idx))
                self.set_current_index(idx)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        # Outer track container
        track_path = QPainterPath()
        track_path.addRoundedRect(rect, 13.0, 13.0)
        painter.fillPath(track_path, QBrush(QColor(22, 22, 26, 235)))
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        painter.drawPath(track_path)

        pill_pad = 3.0
        pill_h = h - (pill_pad * 2.0)

        # Animated sliding pill
        if self._current_w > 10:
            pill_rect = QRectF(self._current_x, pill_pad, self._current_w, pill_h)
            pill_path = QPainterPath()
            pill_path.addRoundedRect(pill_rect, 10.0, 10.0)

            pill_grad = QLinearGradient(pill_rect.topLeft(), pill_rect.bottomLeft())
            pill_grad.setColorAt(0.0, QColor(255, 255, 255, 48))
            pill_grad.setColorAt(1.0, QColor(255, 255, 255, 22))

            painter.fillPath(pill_path, QBrush(pill_grad))
            painter.setPen(QPen(QColor(255, 255, 255, 55), 1.0))
            painter.drawPath(pill_path)

        # Render labels & vector icons with mathematical centering
        count = len(self.items)
        if count == 0:
            return

        slot_w = (w - (pill_pad * 2.0)) / float(count)
        for idx, (label_txt, icon_name) in enumerate(self.items):
            is_active = (idx == self.current_index)
            slot_left = pill_pad + (idx * slot_w)

            icon_color = "#FFFFFF" if is_active else "#98989D"
            pix = get_svg_pixmap(icon_name, 14, icon_color)

            font = get_ui_font(10, QFont.DemiBold if is_active else QFont.Medium)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(label_txt)
            gap = 8.0
            content_w = 14.0 + gap + text_w
            start_x = slot_left + ((slot_w - content_w) / 2.0)

            # Draw icon vertically centered
            icon_y = (h - 14.0) / 2.0
            painter.drawPixmap(int(round(start_x)), int(round(icon_y)), pix)

            # Draw text vertically centered across full slot height
            text_rect = QRectF(start_x + 14.0 + gap, 0.0, text_w + 4.0, h)
            painter.setPen(QColor(255, 255, 255, 255) if is_active else QColor(152, 152, 157, 230))
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label_txt)


LiquidSlidingSegmentedControl = SlidingSegmentedControl


class BentoMetricCard(QFrame):
    """Metric card with vector SVG icon."""
    def __init__(self, title: str, value: str, subtitle: str, accent_color: str = "#0A84FF", icon_name: str = "bolt", parent=None):
        super().__init__(parent)
        self.setObjectName("BentoCard")
        self.accent_color = accent_color
        self.icon_name = icon_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header: Vector Icon + Title
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(16, 16)
        self.lbl_icon.setPixmap(get_svg_pixmap(icon_name, 16, accent_color))
        self.lbl_icon.setStyleSheet("border: none; background: transparent;")
        top_row.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #8E8E93; letter-spacing: 0.8px; border: none; background: transparent;")
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()

        layout.addLayout(top_row)

        # Big Stat Value
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("font-size: 24px; font-weight: 700; color: #FFFFFF; line-height: 1.1; border: none; background: transparent;")
        layout.addWidget(self.lbl_value)

        # Subtitle
        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #8E8E93; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self.setStyleSheet("""
            #BentoCard {
                background-color: rgba(36, 36, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 14px;
            }
            #BentoCard:hover {
                background-color: rgba(44, 44, 52, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

    def update_data(self, title: str, value: str, subtitle: str):
        self.lbl_title.setText(title.upper())
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)
        self.lbl_icon.setPixmap(get_svg_pixmap(self.icon_name, 16, self.accent_color))


class MultiChartAnalyticsWidget(QWidget):
    """
    Multi-chart analytics widget supporting:
    - 'volume': Daily/hourly bar chart
    - 'speed': Pace velocity spline curve (WPM)
    - 'sources': Source distribution breakdown (Microphone vs File imports)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

        self.mode = "volume"        # 'volume', 'speed', 'sources'
        self.timeframe = "7d"       # '7d', '14d', 'hourly'
        self.lang = "ru"

        self.volume_data: List[Dict[str, Any]] = []
        self.speed_data: List[Dict[str, Any]] = []
        self.source_data: Dict[str, Any] = {}

        self._anim_progress = 0.0
        self._last_frame_time = time.perf_counter()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(4)
        self._anim_timer.timeout.connect(self._step_animation)

        # Hover state
        self._hovered_idx = -1
        self._hover_pos = QPointF(0, 0)

    def set_chart_data(self, volume_data, speed_data, source_data, mode: str = "volume", timeframe: str = "7d", lang: str = "ru"):
        self.volume_data = volume_data
        self.speed_data = speed_data
        self.source_data = source_data
        self.mode = mode
        self.timeframe = timeframe
        self.lang = lang
        self._hovered_idx = -1
        self.start_animation()

    def start_animation(self):
        self._anim_progress = 0.0
        self._last_frame_time = time.perf_counter()
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()

    def _step_animation(self):
        now = time.perf_counter()
        dt = max(0.001, min(0.05, now - self._last_frame_time))
        self._last_frame_time = now

        speed = 10.0
        alpha = 1.0 - math.exp(-speed * dt)
        self._anim_progress += (1.0 - self._anim_progress) * alpha

        if abs(1.0 - self._anim_progress) < 0.002:
            self._anim_progress = 1.0
            self._anim_timer.stop()

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        self._hover_pos = pos

        if self.mode == "volume":
            data = self.volume_data
            count = len(data)
            if count == 0:
                return
            w = float(self.width())
            chart_left = 20.0
            chart_w = w - 40.0
            slot_w = chart_w / float(count)
            idx = int((pos.x() - chart_left) / slot_w)
            if 0 <= idx < count:
                if self._hovered_idx != idx:
                    self._hovered_idx = idx
                    self.update()
            else:
                if self._hovered_idx != -1:
                    self._hovered_idx = -1
                    self.update()

        elif self.mode == "speed":
            data = self.speed_data
            count = len(data)
            if count < 2:
                return
            w = float(self.width())
            chart_left = 24.0
            chart_w = w - 48.0
            step_x = chart_w / float(count - 1)
            idx = int(round((pos.x() - chart_left) / step_x))
            if 0 <= idx < count:
                if self._hovered_idx != idx:
                    self._hovered_idx = idx
                    self.update()
            else:
                if self._hovered_idx != -1:
                    self._hovered_idx = -1
                    self.update()

        elif self.mode == "sources":
            self.update()

    def leaveEvent(self, event):
        if self._hovered_idx != -1:
            self._hovered_idx = -1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        # Container Card (Liquid Glass Background)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(rect, 14.0, 14.0)
        painter.fillPath(bg_path, QBrush(QColor(32, 32, 38, 195)))
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        painter.drawPath(bg_path)

        ease = min(1.0, max(0.0, self._anim_progress))

        if self.mode == "volume":
            self._paint_volume_bars(painter, w, h, ease)
        elif self.mode == "speed":
            self._paint_speed_spline(painter, w, h, ease)
        elif self.mode == "sources":
            self._paint_sources_donut(painter, w, h, ease)

    def _paint_volume_bars(self, painter: QPainter, w: float, h: float, ease: float):
        data = self.volume_data
        if not data:
            painter.setPen(QColor(142, 142, 147))
            painter.setFont(get_ui_font(11))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, t("analytics_no_data", self.lang))
            return

        pad_top = 34.0
        pad_bottom = 36.0
        pad_x = 22.0
        chart_top = pad_top
        chart_bottom = h - pad_bottom
        chart_h = chart_bottom - chart_top
        chart_w = w - (pad_x * 2.0)

        max_val = max([item.get("words", 0) for item in data] + [10])
        max_val = max(10, int(math.ceil(max_val * 1.18)))

        # Guidelines
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1.0, Qt.DashLine))
        for frac in (0.33, 0.66, 1.0):
            gy = chart_bottom - (chart_h * frac)
            painter.drawLine(QPointF(pad_x, gy), QPointF(w - pad_x, gy))

        # Average line
        total_words = sum(item.get("words", 0) for item in data)
        count = len(data)
        avg_words = int(total_words / count) if count > 0 else 0
        if avg_words > 0 and count <= 14:
            avg_y = chart_bottom - (min(1.0, float(avg_words) / float(max_val)) * chart_h)
            painter.setPen(QPen(QColor(255, 159, 10, 90), 1.0, Qt.DashDotLine))
            painter.drawLine(QPointF(pad_x, avg_y), QPointF(w - pad_x, avg_y))

        slot_w = chart_w / float(count)
        bar_w = max(8.0, min(36.0, slot_w * 0.58))
        hover_info = None

        for idx, item in enumerate(data):
            words = item.get("words", 0)
            is_today = item.get("is_today", False)
            cx = pad_x + (slot_w * idx) + (slot_w / 2.0)

            target_bar_h = max(4.0, (float(words) / float(max_val)) * chart_h) if words > 0 else 4.0
            animated_bar_h = target_bar_h * ease

            bx = cx - (bar_w / 2.0)
            by = chart_bottom - animated_bar_h
            bar_rect = QRectF(bx, by, bar_w, animated_bar_h)
            bar_path = QPainterPath()
            bar_radius = min(bar_w / 2.0, 7.0)
            bar_path.addRoundedRect(bar_rect, bar_radius, bar_radius)

            is_hovered = (idx == self._hovered_idx)
            if is_hovered:
                hover_info = (cx, by, item)

            bar_grad = QLinearGradient(bx, by, bx, chart_bottom)
            if is_today:
                if is_hovered:
                    bar_grad.setColorAt(0.0, QColor(52, 199, 89, 255))
                    bar_grad.setColorAt(1.0, QColor(10, 132, 255, 230))
                else:
                    bar_grad.setColorAt(0.0, QColor(48, 209, 88, 240))
                    bar_grad.setColorAt(1.0, QColor(10, 132, 255, 180))
            else:
                if is_hovered:
                    bar_grad.setColorAt(0.0, QColor(100, 180, 255, 255))
                    bar_grad.setColorAt(1.0, QColor(94, 92, 230, 235))
                else:
                    bar_grad.setColorAt(0.0, QColor(10, 132, 255, 220))
                    bar_grad.setColorAt(1.0, QColor(94, 92, 230, 150))

            if words == 0:
                painter.fillPath(bar_path, QBrush(QColor(255, 255, 255, 20)))
            else:
                painter.fillPath(bar_path, QBrush(bar_grad))
                if is_hovered:
                    painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
                    painter.drawPath(bar_path)

            # Axis label
            if self.timeframe in ("7d", "14d"):
                day_txt = item.get("day_ru" if self.lang == "ru" else "day_en", "")
                if count > 7 and idx % 2 != 0 and not is_today:
                    day_txt = ""  # Thin out labels on 14d
            else:
                hr = item.get("hour", 0)
                day_txt = f"{hr:02d}" if hr % 3 == 0 else ""

            label_rect = QRectF(cx - (slot_w / 2.0), chart_bottom + 8.0, slot_w, 20.0)
            painter.setFont(get_ui_font(9, QFont.DemiBold if is_today else QFont.Normal))
            painter.setPen(QColor(255, 255, 255, 240) if is_today else QColor(142, 142, 147, 200))
            painter.drawText(label_rect, Qt.AlignCenter, day_txt)

            # Value label
            if words > 0 and animated_bar_h > 18.0 and count <= 10:
                top_label_rect = QRectF(cx - 30.0, by - 17.0, 60.0, 16.0)
                painter.setFont(get_ui_font(8, QFont.DemiBold))
                painter.setPen(QColor(255, 255, 255, 210) if is_today else QColor(180, 180, 185, 180))
                painter.drawText(top_label_rect, Qt.AlignCenter, f"{words:,}")

        # Hover Tooltip
        if hover_info:
            self._paint_glass_tooltip(painter, w, hover_info[0], hover_info[1], hover_info[2], "volume")

    def _paint_speed_spline(self, painter: QPainter, w: float, h: float, ease: float):
        data = self.speed_data
        count = len(data)
        if count < 2:
            painter.setPen(QColor(142, 142, 147))
            painter.setFont(get_ui_font(11))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, t("analytics_no_data", self.lang))
            return

        pad_top = 34.0
        pad_bottom = 36.0
        pad_x = 28.0
        chart_top = pad_top
        chart_bottom = h - pad_bottom
        chart_h = chart_bottom - chart_top
        chart_w = w - (pad_x * 2.0)

        max_wpm = max([item.get("wpm", 0) for item in data] + [160])
        max_wpm = max(160, int(math.ceil(max_wpm * 1.2)))

        # Guidelines
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1.0, Qt.DashLine))
        for frac in (0.33, 0.66, 1.0):
            gy = chart_bottom - (chart_h * frac)
            painter.drawLine(QPointF(pad_x, gy), QPointF(w - pad_x, gy))

        # Standard keyboard typing reference line (40 WPM)
        kb_y = chart_bottom - ((40.0 / float(max_wpm)) * chart_h)
        painter.setPen(QPen(QColor(142, 142, 147, 80), 1.0, Qt.DotLine))
        painter.drawLine(QPointF(pad_x, kb_y), QPointF(w - pad_x, kb_y))
        painter.setFont(get_ui_font(8))
        painter.setPen(QColor(142, 142, 147, 150))
        painter.drawText(QRectF(pad_x + 2.0, kb_y - 14.0, 170.0, 12.0), Qt.AlignLeft, t("chart_kb_reference_line", self.lang))

        # Compute point coordinates
        step_x = chart_w / float(count - 1)
        points: List[QPointF] = []
        for idx, item in enumerate(data):
            wpm = float(item.get("wpm", 0))
            px = pad_x + (float(idx) * step_x)
            py = chart_bottom - ((wpm / float(max_wpm)) * chart_h * ease)
            points.append(QPointF(px, py))

        # Draw smooth cubic spline curve & filled area
        spline_path = QPainterPath()
        spline_path.moveTo(points[0])

        for i in range(len(points) - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(len(points) - 1, i + 2)]

            # Catmull-Rom to Cubic Bezier conversion
            c1 = p1 + (p2 - p0) / 6.0
            c2 = p2 - (p3 - p1) / 6.0
            spline_path.cubicTo(c1, c2, p2)

        # Gradient area fill beneath spline
        area_path = QPainterPath(spline_path)
        area_path.lineTo(points[-1].x(), chart_bottom)
        area_path.lineTo(points[0].x(), chart_bottom)
        area_path.closeSubpath()

        area_grad = QLinearGradient(0, chart_top, 0, chart_bottom)
        area_grad.setColorAt(0.0, QColor(10, 132, 255, int(90 * ease)))
        area_grad.setColorAt(0.8, QColor(94, 92, 230, int(30 * ease)))
        area_grad.setColorAt(1.0, QColor(94, 92, 230, 0))
        painter.fillPath(area_path, QBrush(area_grad))

        # Stroke spline line
        line_pen = QPen(QColor(10, 132, 255, int(240 * ease)), 2.5)
        painter.strokePath(spline_path, line_pen)

        hover_info = None

        # Data nodes
        for idx, pt in enumerate(points):
            item = data[idx]
            is_hovered = (idx == self._hovered_idx)
            is_today = item.get("is_today", False)

            if is_hovered:
                hover_info = (pt.x(), pt.y(), item)

            node_r = 5.0 if is_hovered else 3.5
            painter.setBrush(QBrush(QColor(52, 199, 89) if is_today else QColor(255, 255, 255)))
            painter.setPen(QPen(QColor(10, 132, 255) if not is_today else QColor(30, 30, 35), 1.5))
            painter.drawEllipse(pt, node_r, node_r)

            # Axis labels
            day_txt = item.get("day_ru" if self.lang == "ru" else "day_en", "")
            label_rect = QRectF(pt.x() - 20.0, chart_bottom + 8.0, 40.0, 20.0)
            painter.setFont(get_ui_font(9, QFont.DemiBold if is_today else QFont.Normal))
            painter.setPen(QColor(255, 255, 255, 240) if is_today else QColor(142, 142, 147, 200))
            painter.drawText(label_rect, Qt.AlignCenter, day_txt)

        if hover_info:
            self._paint_glass_tooltip(painter, w, hover_info[0], hover_info[1], hover_info[2], "speed")

    def _paint_sources_donut(self, painter: QPainter, w: float, h: float, ease: float):
        src = self.source_data
        mic_pct = src.get("mic_percent", 100.0)
        file_pct = src.get("file_percent", 0.0)
        mic_cnt = src.get("mic_count", 0)
        file_cnt = src.get("file_count", 0)
        mic_words = src.get("mic_words", 0)
        file_words = src.get("file_words", 0)

        cx = w * 0.30
        cy = h * 0.50

        # Ring 1: Microphone (Outer, Emerald Green)
        r_mic = min(h * 0.38, 76.0)
        track_w = 11.0
        rect_mic = QRectF(cx - r_mic, cy - r_mic, r_mic * 2.0, r_mic * 2.0)

        # Background track for Mic
        painter.setPen(QPen(QColor(48, 209, 88, 38), track_w, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect_mic, 0, 360 * 16)

        # Active arc for Mic
        sweep_mic = int(round((mic_pct / 100.0) * 360.0 * 16.0 * ease))
        if sweep_mic > 0:
            painter.setPen(QPen(QColor(48, 209, 88), track_w, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(rect_mic, 90 * 16, -sweep_mic)

        # Ring 2: Audio Files (Inner, Amber Orange)
        r_file = r_mic - 18.0
        rect_file = QRectF(cx - r_file, cy - r_file, r_file * 2.0, r_file * 2.0)

        # Background track for File
        painter.setPen(QPen(QColor(255, 159, 10, 38), track_w, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect_file, 0, 360 * 16)

        # Active arc for File
        sweep_file = int(round((file_pct / 100.0) * 360.0 * 16.0 * ease))
        if sweep_file > 0:
            painter.setPen(QPen(QColor(255, 159, 10), track_w, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(rect_file, 90 * 16, -sweep_file)

        # Center dominant readout
        painter.setFont(get_ui_font(15, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        dom_pct = int(round(mic_pct)) if mic_pct >= file_pct else int(round(file_pct))
        painter.drawText(QRectF(cx - 40.0, cy - 14.0, 80.0, 20.0), Qt.AlignCenter, f"{dom_pct}%")
        painter.setFont(get_ui_font(8, QFont.Medium))
        painter.setPen(QColor(142, 142, 147))
        dom_label = t("source_mic", self.lang) if mic_pct >= file_pct else t("source_file", self.lang)
        painter.drawText(QRectF(cx - 40.0, cy + 8.0, 80.0, 14.0), Qt.AlignCenter, dom_label)

        # Right Side: 2 Apple Frosted Glass Cards
        card_x = w * 0.54
        card_w = w - card_x - 16.0
        card_h = 66.0

        # Card 1: Microphone Breakdown
        card1_y = cy - 72.0
        c1_path = QPainterPath()
        c1_path.addRoundedRect(QRectF(card_x, card1_y, card_w, card_h), 10.0, 10.0)
        painter.fillPath(c1_path, QBrush(QColor(24, 24, 28, 210)))
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        painter.drawPath(c1_path)

        painter.drawPixmap(int(card_x + 12.0), int(card1_y + 11.0), get_svg_pixmap("mic", 14, "#30D158"))
        painter.setFont(get_ui_font(9, QFont.Bold))
        painter.setPen(QColor(48, 209, 88))
        painter.drawText(QRectF(card_x + 32.0, card1_y + 10.0, card_w - 40.0, 16.0), Qt.AlignLeft | Qt.AlignVCenter, t("source_mic_title", self.lang).upper())

        painter.setFont(get_ui_font(12, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        words_unit = t('unit_words_short', self.lang, val='').replace('0', '').strip()
        painter.drawText(QRectF(card_x + 12.0, card1_y + 28.0, card_w - 24.0, 18.0), Qt.AlignLeft | Qt.AlignVCenter, f"{mic_words:,} {words_unit} ({mic_pct}%)")

        painter.setFont(get_ui_font(9))
        painter.setPen(QColor(142, 142, 147))
        rec_sub = t('records_total_sub', self.lang, count=mic_cnt)
        painter.drawText(QRectF(card_x + 12.0, card1_y + 46.0, card_w - 24.0, 14.0), Qt.AlignLeft, rec_sub)

        # Card 2: File Import Breakdown
        card2_y = cy + 4.0
        c2_path = QPainterPath()
        c2_path.addRoundedRect(QRectF(card_x, card2_y, card_w, card_h), 10.0, 10.0)
        painter.fillPath(c2_path, QBrush(QColor(24, 24, 28, 210)))
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        painter.drawPath(c2_path)

        painter.drawPixmap(int(card_x + 12.0), int(card2_y + 11.0), get_svg_pixmap("folder", 14, "#FF9F0A"))
        painter.setFont(get_ui_font(9, QFont.Bold))
        painter.setPen(QColor(255, 159, 10))
        painter.drawText(QRectF(card_x + 32.0, card2_y + 10.0, card_w - 40.0, 16.0), Qt.AlignLeft | Qt.AlignVCenter, t("source_file_title", self.lang).upper())

        painter.setFont(get_ui_font(12, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(card_x + 12.0, card2_y + 28.0, card_w - 24.0, 18.0), Qt.AlignLeft | Qt.AlignVCenter, f"{file_words:,} {words_unit} ({file_pct}%)")

        painter.setFont(get_ui_font(9))
        painter.setPen(QColor(142, 142, 147))
        file_sub = t('records_total_sub', self.lang, count=file_cnt)
        painter.drawText(QRectF(card_x + 12.0, card2_y + 46.0, card_w - 24.0, 14.0), Qt.AlignLeft, file_sub)

    def _paint_glass_tooltip(self, painter: QPainter, w: float, tx: float, ty: float, item: Dict[str, Any], chart_kind: str):
        tip_w = 160.0
        tip_h = 56.0
        tip_x = max(10.0, min(w - tip_w - 10.0, tx - (tip_w / 2.0)))
        tip_y = max(10.0, ty - tip_h - 10.0)

        tip_rect = QRectF(tip_x, tip_y, tip_w, tip_h)
        tip_path = QPainterPath()
        tip_path.addRoundedRect(tip_rect, 9.0, 9.0)

        # Frosted glass card
        painter.fillPath(tip_path, QBrush(QColor(18, 18, 22, 245)))
        painter.setPen(QPen(QColor(255, 255, 255, 48), 1.0))
        painter.drawPath(tip_path)

        # Header string
        if self.timeframe in ("7d", "14d"):
            header_str = f"{item.get('day_ru' if self.lang == 'ru' else 'day_en', '')}, {item.get('short_date', '')}"
            if item.get("is_today"):
                header_str += f" ({t('chart_today_badge', self.lang)})"
        else:
            header_str = item.get("hour_label", "")

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(get_ui_font(9, QFont.Bold))
        painter.drawText(QRectF(tip_x + 10.0, tip_y + 7.0, tip_w - 20.0, 16.0), Qt.AlignLeft, header_str)

        if chart_kind == "volume":
            words = item.get("words", 0)
            mins = item.get("minutes_saved", 0.0)
            sub_str = f"{t('chart_tooltip_words', self.lang, val=words)} • {t('unit_mins_short', self.lang, val=mins)}"
            color = QColor(48, 209, 88) if words > 0 else QColor(142, 142, 147)
        else:
            wpm = item.get("wpm", 0)
            sub_str = t("chart_tooltip_speed", self.lang, val=wpm)
            color = QColor(10, 132, 255) if wpm > 0 else QColor(142, 142, 147)

        painter.setPen(color)
        painter.setFont(get_ui_font(9, QFont.DemiBold))
        painter.drawText(QRectF(tip_x + 10.0, tip_y + 28.0, tip_w - 20.0, 18.0), Qt.AlignLeft, sub_str)


LiquidInteractiveChart = MultiChartAnalyticsWidget


class TranscriptCard(QFrame):
    """Transcript record card with vector SVG icons, animated deletion, and copy feedback."""
    clicked = Signal(str)
    delete_requested = Signal(int)

    def __init__(self, entry_id: int, text: str, created_at: str, duration: float, word_count: int, source: str = "mic", lang: str = "ru", parent=None):
        super().__init__(parent)
        self.entry_id = entry_id
        self.text = text
        self.lang = lang
        self.is_deleting = False
        self._collapse_timer = None
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("TranscriptCard")
        self.setToolTip(t("copy_click_hint", lang))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header Row: Time + Metadata Badges + Actions
        header = QHBoxLayout()
        header.setSpacing(8)

        rel_time = format_relative_time(created_at, lang=lang)
        self.lbl_time = QLabel(rel_time)
        self.lbl_time.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        header.addWidget(self.lbl_time)

        header.addStretch()

        # Source vector badge
        src_is_mic = (source == "mic")
        icon_name = "mic" if src_is_mic else "folder"
        src_label = t("source_mic", lang) if src_is_mic else t("source_file", lang)

        badge_src = QFrame()
        badge_src.setObjectName("BadgeSrc")
        badge_src.setStyleSheet("""
            #BadgeSrc {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
        """)
        bs_layout = QHBoxLayout(badge_src)
        bs_layout.setContentsMargins(5, 2, 6, 2)
        bs_layout.setSpacing(4)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_svg_pixmap(icon_name, 12, "#A1A1A6"))
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        lbl_text = QLabel(src_label)
        lbl_text.setStyleSheet("font-size: 10px; color: #A1A1A6; border: none; background: transparent;")
        bs_layout.addWidget(lbl_icon)
        bs_layout.addWidget(lbl_text)
        header.addWidget(badge_src)

        # Duration & Words badges
        if duration > 0:
            badge_dur = QLabel(t("unit_seconds_short", lang, val=duration))
            badge_dur.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.07);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                    color: #A1A1A6;
                }
            """)
            header.addWidget(badge_dur)

        if word_count > 0:
            badge_words = QLabel(t("unit_words_short", lang, val=word_count))
            badge_words.setStyleSheet("""
                QLabel {
                    background-color: rgba(10, 132, 255, 0.15);
                    border: 1px solid rgba(10, 132, 255, 0.25);
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                    color: #5AC8FA;
                    font-weight: 600;
                }
            """)
            header.addWidget(badge_words)

        # Delete Entry Button with Apple hover micro-interaction
        self.btn_del = QPushButton()
        self.btn_del.setFixedSize(22, 22)
        self.btn_del.setCursor(Qt.PointingHandCursor)
        self.btn_del.setToolTip(t("btn_delete_entry", lang))
        self.btn_del.setIcon(get_svg_icon("trash", 12, "#636366"))
        self.btn_del.clicked.connect(self._on_delete_clicked)
        self.btn_del.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 69, 58, 0.22);
            }
        """)
        header.addWidget(self.btn_del)

        layout.addLayout(header)

        # Content Text
        self.content_label = QLabel(text)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("font-size: 13px; line-height: 1.45; color: #FFFFFF; border: none; background: transparent;")
        layout.addWidget(self.content_label)

        # Copy state indicator
        self.copy_banner = QFrame()
        self.copy_banner.setVisible(False)
        cb_layout = QHBoxLayout(self.copy_banner)
        cb_layout.setContentsMargins(0, 2, 0, 0)
        cb_layout.setSpacing(6)
        check_icon = QLabel()
        check_icon.setPixmap(get_svg_pixmap("check", 12, "#34C759"))
        check_icon.setStyleSheet("border: none; background: transparent;")
        lbl_copied = QLabel(t("copied_to_clipboard", lang))
        lbl_copied.setStyleSheet("color: #34C759; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        cb_layout.addWidget(check_icon)
        cb_layout.addWidget(lbl_copied)
        cb_layout.addStretch()
        layout.addWidget(self.copy_banner)

        self.setStyleSheet("""
            #TranscriptCard {
                background-color: rgba(36, 36, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            #TranscriptCard:hover {
                background-color: rgba(46, 46, 54, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.16);
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

    def _on_delete_clicked(self):
        if self.is_deleting:
            return
        self.is_deleting = True
        self.start_collapse_animation(lambda: self.delete_requested.emit(self.entry_id))

    def start_collapse_animation(self, on_finish):
        self._collapse_start_h = self.height()
        self._collapse_progress = 0.0
        self._collapse_last_time = time.perf_counter()
        self._on_collapse_finish = on_finish

        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setInterval(4)
        self._collapse_timer.timeout.connect(self._step_collapse)
        self._collapse_timer.start()

    def _step_collapse(self):
        now = time.perf_counter()
        dt = max(0.001, min(0.05, now - self._collapse_last_time))
        self._collapse_last_time = now

        self._collapse_progress += dt * 5.2  # ~190 ms total
        if self._collapse_progress >= 1.0:
            self._collapse_timer.stop()
            if self._on_collapse_finish:
                self._on_collapse_finish()
            return

        p = self._collapse_progress
        ease = 1.0 - (1.0 - p) ** 2
        self._opacity_effect.setOpacity(max(0.0, 1.0 - ease))
        new_h = int(self._collapse_start_h * (1.0 - ease))
        self.setFixedHeight(max(0, new_h))

    def mousePressEvent(self, event):
        if self.is_deleting:
            return
        if event.button() == Qt.LeftButton:
            self.copy_banner.setVisible(True)
            QTimer.singleShot(1800, lambda: self.copy_banner.setVisible(False))
            self.clicked.emit(self.text)


class DropZoneWidget(QFrame):
    """Drag & drop zone with vector icon and format badges."""
    def __init__(self, theme: str = "dark", lang: str = "ru", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.lang = lang
        self.is_drag_over = False
        self.setObjectName("DropZone")
        self.setMinimumHeight(170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_upload = QLabel()
        self.icon_upload.setPixmap(get_svg_pixmap("upload", 36, "#0A84FF"))
        self.icon_upload.setAlignment(Qt.AlignCenter)
        self.icon_upload.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.icon_upload)

        self.lbl_icon = QLabel(t("batch_import_hint", lang))
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF; border: none; background: transparent;")
        layout.addWidget(self.lbl_icon)

        # Formats pill row
        formats_row = QHBoxLayout()
        formats_row.setAlignment(Qt.AlignCenter)
        formats_row.setSpacing(6)

        for fmt in [".MP3", ".WAV", ".M4A", ".FLAC", ".OGG", ".AAC"]:
            fmt_lbl = QLabel(fmt)
            fmt_lbl.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.09);
                    border-radius: 5px;
                    padding: 2px 7px;
                    font-size: 10px;
                    color: #A1A1A6;
                    font-weight: 600;
                }
            """)
            formats_row.addWidget(fmt_lbl)

        layout.addLayout(formats_row)

        self.lbl_sub = QLabel(t("batch_drop_sub", lang))
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #8E8E93; border: none; background: transparent;")
        layout.addWidget(self.lbl_sub)

        self._update_style()

    def set_text(self, title: str, subtitle: Optional[str] = None):
        self.lbl_icon.setText(title)
        if subtitle is not None:
            self.lbl_sub.setText(subtitle)
            self.lbl_sub.setVisible(bool(subtitle))

    def setText(self, text: str):
        self.set_text(text)

    def set_drag_over(self, active: bool):
        self.is_drag_over = active
        self._update_style()

    def _update_style(self):
        if self.is_drag_over:
            border_color = "rgba(10, 132, 255, 0.90)"
            bg_color = "rgba(10, 132, 255, 0.16)"
        else:
            border_color = "rgba(255, 255, 255, 0.14)"
            bg_color = "rgba(30, 30, 36, 0.60)"

        self.setStyleSheet(f"""
            #DropZone {{
                border: 1.5px dashed {border_color};
                background-color: {bg_color};
                border-radius: 14px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)


class NavButton(QPushButton):
    """Navigation button with vector SVG icon."""
    def __init__(self, icon_name: str, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(34, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(get_svg_icon(icon_name, 12, "#E5E5EA"))
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                border: 1px solid rgba(255, 255, 255, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.26);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        color = "#E5E5EA" if enabled else "rgba(255, 255, 255, 0.18)"
        self.setIcon(get_svg_icon(self.icon_name, 12, color))


AppleNavButton = NavButton


class QuickHistoryWindow(QWidget):
    """
    Transcript history, productivity analytics, and audio import window.
    """
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

        # App Window Icon
        res_dir = get_resource_dir()
        icon_path = res_dir / "app_icon_64.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setMinimumSize(540, 680)
        self.resize(580, 730)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        self._init_ui()
        self.refresh_list()

    def _init_ui(self):
        lang = self.config["interface_language"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # --- Window Header ---
        header = QHBoxLayout()
        header.setSpacing(10)

        self.title_lbl = QLabel(t("history_title", lang))
        self.title_lbl.setStyleSheet("font-size: 17px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.2px; border: none; background: transparent;")
        header.addWidget(self.title_lbl)

        header.addStretch()

        # Close button with vector SVG
        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setIcon(get_svg_icon("close", 12, "#8E8E93"))
        self.btn_close.clicked.connect(self.hide)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
            }
        """)
        header.addWidget(self.btn_close)
        layout.addLayout(header)

        # --- Liquid Sliding Segmented Navigation (Spring Physics) ---
        tabs = [
            (t("tab_transcripts", lang), "clock"),
            (t("tab_analytics", lang), "bar_chart"),
            (t("tab_import", lang), "upload"),
        ]
        self.segmented_ctrl = LiquidSlidingSegmentedControl(tabs, current_index=0)
        self.segmented_ctrl.segment_changed.connect(self._on_tab_changed)
        layout.addWidget(self.segmented_ctrl)

        # --- Stacked Widget for Tab Views ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # PAGE 0: Transcripts View
        self.page_transcripts = QWidget()
        self._init_transcripts_page()
        self.stack.addWidget(self.page_transcripts)

        # PAGE 1: Liquid Glass Multi-Chart Analytics Dashboard
        self.page_analytics = QWidget()
        self._init_analytics_page()
        self.stack.addWidget(self.page_analytics)

        # PAGE 2: Audio File Import Studio
        self.page_import = QWidget()
        self._init_import_page()
        self.stack.addWidget(self.page_import)

        self.setFont(get_ui_font(10))
        self.setStyleSheet("""
            QuickHistoryWindow, QLabel, QPushButton, QLineEdit {
                font-family: "Segoe UI", "Segoe UI Variable Text", -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
            }
            QuickHistoryWindow {
                background-color: #1A1A1E;
                color: #F5F5F7;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

    def _on_tab_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.refresh_list()
        elif index == 1:
            self._refresh_analytics()

    def _init_transcripts_page(self):
        layout = QVBoxLayout(self.page_transcripts)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Quick Productivity Banner (Preserves test contract)
        self.banner_frame = QFrame()
        self.banner_frame.setObjectName("BannerFrame")
        self.banner_frame.setStyleSheet("""
            #BannerFrame {
                background-color: rgba(36, 36, 42, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        bf_layout = QHBoxLayout(self.banner_frame)
        bf_layout.setContentsMargins(10, 7, 10, 7)
        bf_layout.setSpacing(8)

        self.banner_icon = QLabel()
        self.banner_icon.setPixmap(get_svg_pixmap("bolt", 14, "#30D158"))
        self.banner_icon.setStyleSheet("border: none; background: transparent;")
        bf_layout.addWidget(self.banner_icon)

        self.lbl_stats = QLabel()
        self.lbl_stats.setStyleSheet("color: #A1A1A6; font-size: 12px; font-weight: 500; border: none; background: transparent;")
        bf_layout.addWidget(self.lbl_stats)
        bf_layout.addStretch()
        layout.addWidget(self.banner_frame)

        # Search Bar with Vector Search Icon
        search_box = QFrame()
        search_box.setObjectName("SearchBox")
        search_box.setStyleSheet("""
            #SearchBox {
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.10);
                background-color: rgba(28, 28, 34, 0.75);
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        sb_layout = QHBoxLayout(search_box)
        sb_layout.setContentsMargins(10, 4, 10, 4)
        sb_layout.setSpacing(6)

        search_icon = QLabel()
        search_icon.setPixmap(get_svg_pixmap("search", 14, "#8E8E93"))
        search_icon.setStyleSheet("border: none; background: transparent;")
        sb_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_placeholder", self.config["interface_language"]))
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                color: #FFFFFF;
                font-size: 13px;
                padding: 4px 0;
            }
        """)
        sb_layout.addWidget(self.search_input, 1)
        layout.addWidget(search_box)

        # Scroll area for cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_container.setAttribute(Qt.WA_StyledBackground, True)
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 2, 0, 2)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, 1)

        # Sleek Apple Pagination Bar
        nav_layout = QHBoxLayout()
        self.btn_prev = AppleNavButton("chevron_left")
        self.btn_prev.clicked.connect(self._prev_page)

        self.page_label = QLabel("")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("""
            QLabel {
                color: #A1A1A6;
                font-size: 12px;
                font-weight: 600;
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 4px 16px;
            }
        """)

        self.btn_next = AppleNavButton("chevron_right")
        self.btn_next.clicked.connect(self._next_page)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.page_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)

    def _init_import_page(self):
        layout = QVBoxLayout(self.page_import)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        lang = self.config["interface_language"]

        # Studio Header Card
        header_box = QFrame()
        header_box.setObjectName("ImportHeader")
        header_box.setStyleSheet("""
            #ImportHeader {
                background-color: rgba(36, 36, 42, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        hb_layout = QVBoxLayout(header_box)
        hb_layout.setContentsMargins(16, 14, 16, 14)
        hb_layout.setSpacing(4)

        title_lbl = QLabel(t("import_title", lang))
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF; border: none; background: transparent;")
        hb_layout.addWidget(title_lbl)

        sub_lbl = QLabel(t("import_subtitle", lang))
        sub_lbl.setStyleSheet("font-size: 12px; color: #8E8E93; border: none; background: transparent;")
        sub_lbl.setWordWrap(True)
        hb_layout.addWidget(sub_lbl)
        layout.addWidget(header_box)

        # Big Apple Liquid Glass Drop Zone
        self.drop_zone = DropZoneWidget(theme="dark", lang=lang)
        layout.addWidget(self.drop_zone, 1)

        # Action button: Choose files
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_browse = QPushButton(f"  {t('btn_browse_files', lang)}")
        self.btn_browse.setIcon(get_svg_icon("folder", 15, "#FFFFFF"))
        self.btn_browse.setFixedHeight(38)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #0A84FF;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 10px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #0077ED;
            }
            QPushButton:pressed {
                background-color: #0062C4;
            }
        """)
        self.btn_browse.clicked.connect(self._browse_audio_files)
        btn_layout.addWidget(self.btn_browse)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress bar for batch processing
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 2.5px;
                background-color: rgba(255, 255, 255, 0.08);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0A84FF, stop:1 #30D158);
                border-radius: 2.5px;
            }
        """)
        layout.addWidget(self.progress_bar)

    def _browse_audio_files(self):
        lang = self.config["interface_language"]
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("import_title", lang),
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma);;All Files (*.*)"
        )
        if files:
            self.batch_transcribe_requested.emit(files)

    def _init_analytics_page(self):
        layout = QVBoxLayout(self.page_analytics)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lang = self.config["interface_language"]

        # Bento Grid (2x2)
        grid = QGridLayout()
        grid.setSpacing(10)

        # Card 1: Today Words
        self.card_today = BentoMetricCard(
            title=t("analytics_words_today", lang),
            value="0",
            subtitle=t("records_today_sub", lang, count=0),
            accent_color="#30D158",
            icon_name="bolt"
        )
        grid.addWidget(self.card_today, 0, 0)

        # Card 2: Time Saved
        self.card_saved = BentoMetricCard(
            title=t("analytics_time_saved", lang),
            value=t("unit_mins_short", lang, val=0.0),
            subtitle=t("time_saved_multiplier_sub", lang, mult=3.5),
            accent_color="#0A84FF",
            icon_name="clock"
        )
        grid.addWidget(self.card_saved, 0, 1)

        # Card 3: Speech Pace WPM
        self.card_speed = BentoMetricCard(
            title=t("analytics_speed_wpm", lang),
            value=t("unit_wpm", lang, val=145),
            subtitle=t("speed_compare_sub", lang),
            accent_color="#BF5AF2",
            icon_name="gauge"
        )
        grid.addWidget(self.card_speed, 1, 0)

        # Card 4: All-Time Total
        self.card_total = BentoMetricCard(
            title=t("analytics_total_words", lang),
            value=t("unit_words_total", lang, val=0),
            subtitle=t("records_total_sub", lang, count=0),
            accent_color="#FF9F0A",
            icon_name="trending"
        )
        grid.addWidget(self.card_total, 1, 1)

        layout.addLayout(grid)

        # Multi-Chart Hub Controls
        hub_header = QHBoxLayout()
        hub_header.setSpacing(6)

        # Chart Type Pills: Volume / Speed / Sources
        self.btn_chart_volume = QPushButton(t("chart_tab_volume", lang))
        self.btn_chart_volume.setIcon(get_svg_icon("bar_chart", 12, "#FFFFFF"))
        self.btn_chart_volume.setFixedHeight(26)
        self.btn_chart_volume.setCursor(Qt.PointingHandCursor)
        self.btn_chart_volume.clicked.connect(lambda: self._set_chart_type("volume"))
        hub_header.addWidget(self.btn_chart_volume)

        self.btn_chart_speed = QPushButton(t("chart_tab_speed", lang))
        self.btn_chart_speed.setIcon(get_svg_icon("spline_chart", 12, "#8E8E93"))
        self.btn_chart_speed.setFixedHeight(26)
        self.btn_chart_speed.setCursor(Qt.PointingHandCursor)
        self.btn_chart_speed.clicked.connect(lambda: self._set_chart_type("speed"))
        hub_header.addWidget(self.btn_chart_speed)

        self.btn_chart_sources = QPushButton(t("chart_tab_sources", lang))
        self.btn_chart_sources.setIcon(get_svg_icon("donut_chart", 12, "#8E8E93"))
        self.btn_chart_sources.setFixedHeight(26)
        self.btn_chart_sources.setCursor(Qt.PointingHandCursor)
        self.btn_chart_sources.clicked.connect(lambda: self._set_chart_type("sources"))
        hub_header.addWidget(self.btn_chart_sources)

        hub_header.addStretch()

        # Timeframe Pills: 7d / 14d / Hourly (Only relevant for volume/speed)
        self.timeframe_container = QWidget()
        tc_layout = QHBoxLayout(self.timeframe_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(4)

        self.btn_chart_7d = QPushButton(t("chart_range_7d", lang))
        self.btn_chart_7d.setFixedHeight(24)
        self.btn_chart_7d.setCursor(Qt.PointingHandCursor)
        self.btn_chart_7d.clicked.connect(lambda: self._set_chart_range("7d"))
        tc_layout.addWidget(self.btn_chart_7d)

        self.btn_chart_14d = QPushButton(t("chart_range_14d", lang))
        self.btn_chart_14d.setFixedHeight(24)
        self.btn_chart_14d.setCursor(Qt.PointingHandCursor)
        self.btn_chart_14d.clicked.connect(lambda: self._set_chart_range("14d"))
        tc_layout.addWidget(self.btn_chart_14d)

        self.btn_chart_hourly = QPushButton(t("chart_range_hourly", lang))
        self.btn_chart_hourly.setFixedHeight(24)
        self.btn_chart_hourly.setCursor(Qt.PointingHandCursor)
        self.btn_chart_hourly.clicked.connect(lambda: self._set_chart_range("hourly"))
        tc_layout.addWidget(self.btn_chart_hourly)

        hub_header.addWidget(self.timeframe_container)
        layout.addLayout(hub_header)

        # 240 Hz Liquid Multi-Chart
        self.chart = LiquidInteractiveChart()
        layout.addWidget(self.chart, 1)

        self._active_chart_type = "volume"
        self._active_chart_range = "7d"
        self._update_all_chart_pills()

    def _set_chart_type(self, chart_type: str):
        self._active_chart_type = chart_type
        self.timeframe_container.setVisible(chart_type in ("volume", "speed"))
        self._update_all_chart_pills()
        self._reload_chart_data()

    def _set_chart_range(self, range_mode: str):
        self._active_chart_range = range_mode
        self._update_all_chart_pills()
        self._reload_chart_data()

    def _update_all_chart_pills(self):
        active_type_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.18);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 7px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 10px;
            }
        """
        inactive_type_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                color: #8E8E93;
                font-size: 11px;
                padding: 2px 10px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.06);
            }
        """
        self.btn_chart_volume.setStyleSheet(active_type_style if self._active_chart_type == "volume" else inactive_type_style)
        self.btn_chart_speed.setStyleSheet(active_type_style if self._active_chart_type == "speed" else inactive_type_style)
        self.btn_chart_sources.setStyleSheet(active_type_style if self._active_chart_type == "sources" else inactive_type_style)

        # Range pills
        active_range_style = """
            QPushButton {
                background-color: rgba(10, 132, 255, 0.25);
                border: 1px solid rgba(10, 132, 255, 0.45);
                border-radius: 5px;
                color: #5AC8FA;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 7px;
            }
        """
        inactive_range_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 5px;
                color: #8E8E93;
                font-size: 10px;
                padding: 1px 7px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.05);
            }
        """
        self.btn_chart_7d.setStyleSheet(active_range_style if self._active_chart_range == "7d" else inactive_range_style)
        self.btn_chart_14d.setStyleSheet(active_range_style if self._active_chart_range == "14d" else inactive_range_style)
        self.btn_chart_hourly.setStyleSheet(active_range_style if self._active_chart_range == "hourly" else inactive_range_style)

    def _reload_chart_data(self):
        lang = self.config["interface_language"]
        if self._active_chart_range == "7d":
            vol_data = self.db.get_daily_activity(7)
            speed_data = self.db.get_speed_trend(7)
        elif self._active_chart_range == "14d":
            vol_data = self.db.get_daily_activity(14)
            speed_data = self.db.get_speed_trend(14)
        else:
            vol_data = self.db.get_hourly_activity()
            speed_data = []

        sources_data = self.db.get_source_distribution()

        self.chart.set_chart_data(
            volume_data=vol_data,
            speed_data=speed_data,
            source_data=sources_data,
            mode=self._active_chart_type,
            timeframe=self._active_chart_range,
            lang=lang
        )

    def _on_tab_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 1:
            self._refresh_analytics()

    def _refresh_analytics(self):
        lang = self.config["interface_language"]
        summary = self.db.get_analytics_summary()

        today_words = summary["today_words"]
        today_count = summary["today_count"]
        today_mins = summary["today_minutes_saved"]
        total_words = summary["total_words"]
        total_count = summary["total_count"]
        avg_wpm = summary["avg_wpm"]
        multiplier = summary["speed_multiplier"]

        # Update Bento Cards with full localization
        self.card_today.update_data(
            title=t("analytics_words_today", lang),
            value=f"{today_words:,}",
            subtitle=t("records_today_sub", lang, count=today_count)
        )
        self.card_saved.update_data(
            title=t("analytics_time_saved", lang),
            value=t("unit_mins_short", lang, val=today_mins),
            subtitle=t("time_saved_multiplier_sub", lang, mult=multiplier)
        )
        self.card_speed.update_data(
            title=t("analytics_speed_wpm", lang),
            value=t("unit_wpm", lang, val=avg_wpm),
            subtitle=t("speed_compare_sub", lang)
        )
        self.card_total.update_data(
            title=t("analytics_total_words", lang),
            value=t("unit_words_total", lang, val=total_words),
            subtitle=t("records_total_sub", lang, count=total_count)
        )

        self._reload_chart_data()

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

    def _delete_entry(self, entry_id: int):
        self.db.delete_entry(entry_id)
        self.refresh_list()
        if self.stack.currentIndex() == 1:
            self._refresh_analytics()

    def refresh_list(self):
        lang = self.config["interface_language"]
        query = self.search_input.text()

        # Update quick stats banner
        stats = self.db.get_today_stats()
        words = stats["words"]
        mins = stats["minutes_saved"]
        count = stats["count"]
        if words > 0:
            self.lbl_stats.setText(t("quick_stats_today", lang, words=words, mins=mins, count=count))
        else:
            self.lbl_stats.setText(t("quick_stats_empty", lang))

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
                    entry_id=row["id"],
                    text=row["text"],
                    created_at=row["created_at"],
                    duration=row["duration"],
                    word_count=row.get("word_count", len(row["text"].split())),
                    source=row.get("source", "mic"),
                    lang=lang
                )
                card.clicked.connect(self._copy_to_clipboard)
                card.delete_requested.connect(self._delete_entry)
                self.cards_layout.insertWidget(idx, card)

        self.page_label.setText(t("page_info", lang, current=self.current_page, total=total_pages))
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

    def _copy_to_clipboard(self, text: str):
        QApplication.clipboard().setText(text)

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event):
        # Guarantee 0.0% CPU when window is closed/hidden
        if hasattr(self, "chart") and hasattr(self.chart, "_anim_timer"):
            self.chart._anim_timer.stop()
        if hasattr(self, "segmented_ctrl") and hasattr(self.segmented_ctrl, "_anim_timer"):
            self.segmented_ctrl._anim_timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.hideEvent(event)
        super().closeEvent(event)

