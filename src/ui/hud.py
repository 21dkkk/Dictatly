"""
High-Performance Dynamic Floating Capsule HUD for SuperDictate Windows.
Zero CPU usage when idle (timer completely halts).
Hardware-accelerated glassmorphism, soft ambient shadows, organic audio equalizer,
and emerald neural transcribing pulse.
"""

import math
from typing import Tuple
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, Signal, QObject
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient,
    QRadialGradient, QPainterPath
)
from PySide6.QtWidgets import QWidget

class HUDState:
    IDLE = 0
    RECORDING = 1
    TRANSCRIBING = 2
    SUCCESS = 3

class RecordingHUD(QWidget):
    # Shadow padding around the core capsule
    SHADOW_PADDING = 14

    def __init__(self, size_mode: str = "medium", theme: str = "dark"):
        super().__init__()
        self.state = HUDState.IDLE
        self.size_mode = size_mode
        self.theme = theme
        
        self.volume_level = 0.0      # Current raw volume
        self.smooth_volume = 0.0     # Interpolated volume for butter-smooth bars
        self.animation_phase = 0.0
        self.scale_factor = 0.9      # Pop-in scale factor
        self.opacity = 1.0

        # Window flags: Frameless, Always on Top, Tool window (no taskbar item), No focus stealing
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._update_dimensions()
        self._apply_no_activate()

        # Animation timer (60 FPS) — STOPPED when IDLE to ensure 0.0% CPU usage
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._on_anim_tick)

    def _update_dimensions(self):
        """Set width and height including shadow margins."""
        sizes = {
            "small": (72, 34),
            "medium": (88, 40),
            "large": (104, 46)
        }
        cw, ch = sizes.get(self.size_mode, (88, 40))
        self.capsule_w = cw
        self.capsule_h = ch
        
        # Total widget includes padding for drop shadow
        total_w = cw + (self.SHADOW_PADDING * 2)
        total_h = ch + (self.SHADOW_PADDING * 2)
        self.setFixedSize(total_w, total_h)

    def _apply_no_activate(self):
        """Ensures Windows Window Manager never activates the HUD window, preserving user focus."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE)
        except Exception:
            pass

    def set_mode_and_theme(self, size_mode: str, theme: str):
        self.size_mode = size_mode
        self.theme = theme
        self._update_dimensions()
        self.update()

    def set_state(self, state: int):
        self.state = state
        if state == HUDState.IDLE:
            # STOP timer completely — guarantees ZERO CPU when not dictating
            self.anim_timer.stop()
            self.hide()
        else:
            self.scale_factor = 0.88
            self.opacity = 1.0
            if not self.anim_timer.isActive():
                self.anim_timer.start()
            self.show()
            self.update()

    def set_volume(self, vol: float):
        self.volume_level = vol

    def move_to_caret(self, caret_x: int, caret_y: int):
        """Center capsule horizontally above caret position."""
        w = self.width()
        h = self.height()
        target_x = caret_x - (w // 2)
        # Position capsule so bottom of pill sits 8px above caret
        target_y = caret_y - self.capsule_h - self.SHADOW_PADDING - 6

        # Clamp within active screen geometry
        screen = self.screen()
        if screen:
            geom = screen.geometry()
            target_x = max(geom.left() + 4, min(target_x, geom.right() - w - 4))
            if target_y < geom.top() + 4:
                # If too close to top edge, flip below caret
                target_y = caret_y + 20 - self.SHADOW_PADDING
            target_y = max(geom.top() + 4, min(target_y, geom.bottom() - h - 4))

        self.move(target_x, target_y)

    def _on_anim_tick(self):
        self.animation_phase = (self.animation_phase + 0.09) % (2 * math.pi)
        
        # Smooth volume interpolation (decay/rise)
        target_v = self.volume_level
        self.smooth_volume += (target_v - self.smooth_volume) * 0.35

        # Smooth scale pop-in
        if self.scale_factor < 1.0:
            self.scale_factor += (1.0 - self.scale_factor) * 0.4

        if self.state != HUDState.IDLE:
            self.update()

    def paintEvent(self, event):
        if self.state == HUDState.IDLE:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        pad = self.SHADOW_PADDING
        cw = self.capsule_w
        ch = self.capsule_h
        
        # Calculate scaled capsule rect
        sw = cw * self.scale_factor
        sh = ch * self.scale_factor
        sx = pad + (cw - sw) / 2.0
        sy = pad + (ch - sh) / 2.0
        
        capsule_rect = QRectF(sx, sy, sw, sh)
        radius = sh / 2.0

        # --- 1. Soft Multi-Layer Ambient Shadow ---
        if self.theme == "dark":
            shadow_color = QColor(0, 0, 0, 16)
        else:
            shadow_color = QColor(0, 0, 0, 8)

        for i in range(pad, 0, -2):
            shadow_rect = capsule_rect.adjusted(-i * 0.7, -i * 0.5 + 2, i * 0.7, i * 0.8 + 3)
            shadow_radius = shadow_rect.height() / 2.0
            sh_path = QPainterPath()
            sh_path.addRoundedRect(shadow_rect, shadow_radius, shadow_radius)
            painter.fillPath(sh_path, QBrush(shadow_color))

        # --- 2. Capsule Body with Apple Liquid Glass Gradient ---
        cap_path = QPainterPath()
        cap_path.addRoundedRect(capsule_rect, radius, radius)

        grad = QLinearGradient(capsule_rect.topLeft(), capsule_rect.bottomRight())
        if self.theme == "dark":
            grad.setColorAt(0.0, QColor(14, 14, 17, 246))
            grad.setColorAt(1.0, QColor(4, 4, 6, 252))
            border_top = QColor(255, 255, 255, 38)
            border_bot = QColor(255, 255, 255, 10)
            text_color = QColor(255, 255, 255)
        else:
            grad.setColorAt(0.0, QColor(255, 255, 255, 250))
            grad.setColorAt(1.0, QColor(242, 242, 247, 252))
            border_top = QColor(0, 0, 0, 20)
            border_bot = QColor(0, 0, 0, 8)
            text_color = QColor(20, 20, 22)

        painter.fillPath(cap_path, QBrush(grad))

        # 1px Subtle Glass Specular Border
        border_grad = QLinearGradient(capsule_rect.topLeft(), capsule_rect.bottomLeft())
        border_grad.setColorAt(0.0, border_top)
        border_grad.setColorAt(1.0, border_bot)
        painter.setPen(QPen(QBrush(border_grad), 1.0))
        painter.drawPath(cap_path)

        # --- 3. Interactive State Content ---
        cx = capsule_rect.center().x()
        cy = capsule_rect.center().y()

        if self.state == HUDState.RECORDING:
            # Discreet Apple Mic Indicator (Amber)
            dot_color = QColor(255, 149, 0)  # Apple System Amber
            pulse = (math.sin(self.animation_phase * 2.4) + 1.0) / 2.0
            
            # Subtle low-alpha breath halo
            glow_rad = 5.5 + pulse * 1.5
            glow_color = QColor(255, 149, 0, int(20 + pulse * 25))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(QPoint(int(cx - (sw * 0.26)), int(cy)), glow_rad, glow_rad)

            # Solid 3.5px core dot
            core_rad = 3.2
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(QPoint(int(cx - (sw * 0.26)), int(cy)), core_rad, core_rad)

            # Minimalist Monochrome Equalizer Bars
            bar_color = text_color
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(bar_color))

            num_bars = 4
            spacing = 5.5
            start_x = cx - 1.5
            max_bar_h = sh * 0.52

            for i in range(num_bars):
                phase_offset = i * 0.75
                wave = (math.sin(self.animation_phase * 3.0 + phase_offset) + 1.0) / 2.0
                bar_h = 3.5 + (self.smooth_volume * (max_bar_h - 3.5) * (0.5 + 0.5 * wave))
                bx = start_x + (i * spacing)
                by = cy - (bar_h / 2.0)
                bar_rect = QRectF(bx, by, 2.5, bar_h)
                painter.drawRoundedRect(bar_rect, 1.25, 1.25)

        elif self.state == HUDState.TRANSCRIBING:
            # 3 Minimalist Monochrome Shimmer Dots
            painter.setPen(Qt.NoPen)
            for i in range(3):
                phase = self.animation_phase * 2.6 + (i * 0.85)
                wave = (math.sin(phase) + 1.0) / 2.0
                dot_size = 3.0 + wave * 1.8
                dot_x = cx - 14.0 + (i * 14.0)
                alpha = int(70 + wave * 185)
                color = QColor(text_color.red(), text_color.green(), text_color.blue(), alpha)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPoint(int(dot_x), int(cy)), dot_size, dot_size)

        elif self.state == HUDState.SUCCESS:
            # Minimalist White Checkmark
            check_color = text_color
            pen = QPen(check_color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(int(cx - 7), int(cy + 1), int(cx - 2), int(cy + 6))
            painter.drawLine(int(cx - 2), int(cy + 6), int(cx + 7), int(cy - 4))
