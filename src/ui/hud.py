"""
Floating capsule HUD widget for Dictatly.
Renders active recording state, real-time volume levels, and transcription indicators.
Stops animation timer when idle to eliminate background CPU usage.
"""

import math
from typing import Optional, Tuple
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, Signal, QObject
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient,
    QPainterPath, QGuiApplication
)
from PySide6.QtWidgets import QWidget

class HUDState:
    IDLE = 0
    RECORDING = 1
    TRANSCRIBING = 2
    SUCCESS = 3

CAPSULE_SIZES = {
    "small": (74, 32),
    "medium": (96, 40),
    "large": (124, 48)
}

def draw_capsule_hud(
    painter: QPainter,
    capsule_rect: QRectF,
    animation_phase: float,
    smooth_volume: float,
    state: int = HUDState.RECORDING,
    draw_shadow: bool = True
):
    """
    Core vector renderer for Dictatly dark glass capsule.
    Scales all internal mic dot, equalizer bars, shimmer dots, and checkmark
    proportionally to capsule width and height.
    """
    sw = capsule_rect.width()
    sh = capsule_rect.height()
    radius = sh / 2.0
    cx = capsule_rect.center().x()
    cy = capsule_rect.center().y()

    # 1. Soft Ambient Multi-Layer Shadow
    if draw_shadow:
        shadow_color = QColor(0, 0, 0, 16)
        for i in range(12, 0, -2):
            shadow_rect = capsule_rect.adjusted(-i * 0.6, -i * 0.4 + 2, i * 0.6, i * 0.7 + 3)
            shadow_radius = shadow_rect.height() / 2.0
            sh_path = QPainterPath()
            sh_path.addRoundedRect(shadow_rect, shadow_radius, shadow_radius)
            painter.fillPath(sh_path, QBrush(shadow_color))

    # 2. Dark Glass Capsule Body
    cap_path = QPainterPath()
    cap_path.addRoundedRect(capsule_rect, radius, radius)

    grad = QLinearGradient(capsule_rect.topLeft(), capsule_rect.bottomRight())
    grad.setColorAt(0.0, QColor(16, 16, 20, 248))
    grad.setColorAt(1.0, QColor(6, 6, 8, 252))
    painter.fillPath(cap_path, QBrush(grad))

    # 1px Subtle Glass Specular Border
    border_grad = QLinearGradient(capsule_rect.topLeft(), capsule_rect.bottomLeft())
    border_grad.setColorAt(0.0, QColor(255, 255, 255, 42))
    border_grad.setColorAt(1.0, QColor(255, 255, 255, 12))
    painter.setPen(QPen(QBrush(border_grad), 1.0))
    painter.drawPath(cap_path)

    # 3. State Content
    if state == HUDState.RECORDING:
        # Amber Mic Dot (proportional to height)
        dot_color = QColor(255, 149, 0)
        pulse = (math.sin(animation_phase * 2.4) + 1.0) / 2.0
        glow_rad = (sh * 0.13) + pulse * 1.5
        glow_color = QColor(255, 149, 0, int(22 + pulse * 25))
        core_rad = max(2.8, sh * 0.082)

        dot_center_x = cx - (sw * 0.25)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(QPointF(dot_center_x, cy), glow_rad, glow_rad)

        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(dot_center_x, cy), core_rad, core_rad)

        # Equalizer Bars (proportional to sw and sh)
        bar_color = QColor(255, 255, 255)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bar_color))

        num_bars = 4
        bar_w = max(2.2, sh * 0.062)
        spacing = max(4.5, sh * 0.135)
        start_x = cx - (spacing * 0.25)
        max_bar_h = sh * 0.52

        for i in range(num_bars):
            phase_offset = i * 0.75
            wave = (math.sin(animation_phase * 3.0 + phase_offset) + 1.0) / 2.0
            bar_h = max(3.2, min(max_bar_h, 3.2 + (smooth_volume * (max_bar_h - 3.2) * (0.5 + 0.5 * wave))))
            bx = start_x + (i * spacing)
            by = cy - (bar_h / 2.0)
            bar_rect = QRectF(bx, by, bar_w, bar_h)
            painter.drawRoundedRect(bar_rect, bar_w / 2.0, bar_w / 2.0)

    elif state == HUDState.TRANSCRIBING:
        painter.setPen(Qt.NoPen)
        dot_spacing = max(11.0, sh * 0.32)
        dot_size = max(2.8, sh * 0.075)
        for i in range(3):
            phase = animation_phase * 2.6 + (i * 0.85)
            wave = (math.sin(phase) + 1.0) / 2.0
            ds = dot_size + wave * 1.8
            dot_x = cx - dot_spacing + (i * dot_spacing)
            alpha = int(70 + wave * 185)
            painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
            painter.drawEllipse(QPointF(dot_x, cy), ds, ds)

    elif state == HUDState.SUCCESS:
        pen = QPen(QColor(255, 255, 255), max(1.8, sh * 0.045), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        check_w = sh * 0.32
        p1 = QPointF(cx - check_w * 0.45, cy + 1)
        p2 = QPointF(cx - check_w * 0.15, cy + check_w * 0.35)
        p3 = QPointF(cx + check_w * 0.45, cy - check_w * 0.3)
        painter.drawLine(p1, p2)
        painter.drawLine(p2, p3)

class CapsulePreviewCanvas(QWidget):
    """
    Embedded live preview widget for Settings Window.
    Renders the dark glass capsule with active animated equalizer bars
    so the user sees instantaneous size changes right inside the settings dialog.
    """
    def __init__(self, size_mode: str = "medium", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.size_mode = size_mode
        self.animation_phase = 0.0
        self.smooth_volume = 0.45
        self.setFixedHeight(66)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.timer = QTimer(self)
        self.timer.setInterval(24)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def set_size_mode(self, size_mode: str):
        self.size_mode = size_mode
        self.update()

    def _on_tick(self):
        self.animation_phase = (self.animation_phase + 0.09) % (2 * math.pi)
        # Gentle synthetic breathing volume for preview
        self.smooth_volume = 0.35 + 0.25 * math.sin(self.animation_phase * 1.5)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        cw, ch = CAPSULE_SIZES.get(self.size_mode, (96, 40))
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        capsule_rect = QRectF(cx - (cw / 2.0), cy - (ch / 2.0), cw, ch)

        draw_capsule_hud(
            painter=painter,
            capsule_rect=capsule_rect,
            animation_phase=self.animation_phase,
            smooth_volume=self.smooth_volume,
            state=HUDState.RECORDING,
            draw_shadow=True
        )

class RecordingHUD(QWidget):
    SHADOW_PADDING = 14

    def __init__(self, size_mode: str = "medium", theme: str = "dark"):
        super().__init__()
        self.state = HUDState.IDLE
        self.size_mode = size_mode
        self.theme = "dark"
        
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
        cw, ch = CAPSULE_SIZES.get(self.size_mode, (96, 40))
        self.capsule_w = cw
        self.capsule_h = ch
        
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

    def set_mode_and_theme(self, size_mode: str, theme: str = "dark"):
        self.size_mode = size_mode
        self.theme = "dark"
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
        target_y = caret_y - self.capsule_h - self.SHADOW_PADDING - 6

        # Multi-monitor support: resolve screen directly containing the caret coordinates
        screen = QGuiApplication.screenAt(QPoint(caret_x, caret_y)) or self.screen()
        if screen:
            geom = screen.geometry()
            target_x = max(geom.left() + 4, min(target_x, geom.right() - w - 4))
            if target_y < geom.top() + 4:
                target_y = caret_y + 20 - self.SHADOW_PADDING
            target_y = max(geom.top() + 4, min(target_y, geom.bottom() - h - 4))

        self.move(target_x, target_y)

    def _on_anim_tick(self):
        self.animation_phase = (self.animation_phase + 0.09) % (2 * math.pi)
        
        target_v = self.volume_level
        self.smooth_volume += (target_v - self.smooth_volume) * 0.35

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
        
        sw = cw * self.scale_factor
        sh = ch * self.scale_factor
        sx = pad + (cw - sw) / 2.0
        sy = pad + (ch - sh) / 2.0
        
        capsule_rect = QRectF(sx, sy, sw, sh)

        draw_capsule_hud(
            painter=painter,
            capsule_rect=capsule_rect,
            animation_phase=self.animation_phase,
            smooth_volume=self.smooth_volume,
            state=self.state,
            draw_shadow=True
        )
