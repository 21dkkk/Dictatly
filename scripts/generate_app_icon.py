import sys
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QImage, QPainter, QColor, QBrush, QPen,
    QLinearGradient, QPainterPath
)
from PySide6.QtWidgets import QApplication

def create_apple_squircle_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path

def generate_icon(size: int = 512) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    pad = size * 0.05
    rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)
    radius = rect.width() * 0.225  # Apple standard 22.5% squircle corner

    # 1. Subtle drop shadow
    shadow_rect = rect.adjusted(0, size * 0.02, 0, size * 0.02)
    shadow_path = create_apple_squircle_path(shadow_rect, radius)
    painter.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 45)))

    # 2. Main Apple Squircle body (Deep Space Titanium / Graphite gradient)
    squircle_path = create_apple_squircle_path(rect, radius)
    body_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    body_grad.setColorAt(0.0, QColor(42, 42, 46))    # Warm graphite top
    body_grad.setColorAt(0.5, QColor(28, 28, 30))    # Deep space gray
    body_grad.setColorAt(1.0, QColor(18, 18, 20))    # Dark obsidian base
    painter.fillPath(squircle_path, QBrush(body_grad))

    # 3. Inner Specular Highlight Rim (Apple Liquid Glass look)
    rim_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    rim_grad.setColorAt(0.0, QColor(255, 255, 255, 60))
    rim_grad.setColorAt(0.4, QColor(255, 255, 255, 15))
    rim_grad.setColorAt(1.0, QColor(0, 0, 0, 80))
    painter.setPen(QPen(QBrush(rim_grad), size * 0.006))
    painter.drawPath(squircle_path)

    # 4. Minimalist Vector Soundwaves & Microphone Emblem
    cx = rect.center().x()
    cy = rect.center().y()

    # Dynamic Minimalist Audio Waveform Bars (Dictatly emblem)
    bars = [
        (0.40, 0.45),
        (0.65, 0.70),
        (1.00, 1.00),
        (0.75, 0.75),
        (0.45, 0.50),
    ]
    num_bars = len(bars)
    bar_w = size * 0.046
    bar_gap = size * 0.042
    total_w = (num_bars * bar_w) + ((num_bars - 1) * bar_gap)
    start_x = cx - (total_w / 2.0)
    max_h = size * 0.38

    painter.setPen(Qt.NoPen)

    for i, (scale_l, scale_r) in enumerate(bars):
        h = max_h * scale_l
        bx = start_x + (i * (bar_w + bar_gap))
        by = cy - (h / 2.0)
        bar_rect = QRectF(bx, by, bar_w, h)
        r = bar_w / 2.0

        bar_grad = QLinearGradient(bar_rect.topLeft(), bar_rect.bottomLeft())
        if i == 2:
            # Center hero bar: pure crisp white with titanium glow
            bar_grad.setColorAt(0.0, QColor(255, 255, 255))
            bar_grad.setColorAt(1.0, QColor(235, 235, 240))
        else:
            bar_grad.setColorAt(0.0, QColor(240, 240, 245, 230))
            bar_grad.setColorAt(1.0, QColor(190, 190, 198, 200))

        painter.setBrush(QBrush(bar_grad))
        painter.drawRoundedRect(bar_rect, r, r)

    painter.end()
    return image

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    res_dir = Path(__file__).resolve().parent.parent / "resources"
    res_dir.mkdir(parents=True, exist_ok=True)

    # Generate 512x512 PNG
    img512 = generate_icon(512)
    img512.save(str(res_dir / "app_icon.png"), "PNG")

    # Generate 64x64 PNG for UI headers / small icons
    img64 = img512.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    img64.save(str(res_dir / "app_icon_64.png"), "PNG")

    print(f"Icons generated in {res_dir}")

if __name__ == "__main__":
    main()
