"""
SVG icon loader and cache for Dictatly UI controls.
"""

from pathlib import Path
from typing import Dict, Tuple, Optional
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QIcon
from PySide6.QtSvg import QSvgRenderer

ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"

class SvgIconManager:
    _renderers: Dict[str, QSvgRenderer] = {}
    _pixmap_cache: Dict[Tuple[str, int, int, str], QPixmap] = {}

    @classmethod
    def _get_renderer(cls, icon_name: str) -> Optional[QSvgRenderer]:
        if icon_name in cls._renderers:
            return cls._renderers[icon_name]
        
        path = ICONS_DIR / f"{icon_name}.svg"
        if not path.exists():
            return None
        
        renderer = QSvgRenderer(str(path))
        if renderer.isValid():
            cls._renderers[icon_name] = renderer
            return renderer
        return None

    @classmethod
    def get_pixmap(cls, icon_name: str, size: int = 16, color: str = "#FFFFFF") -> QPixmap:
        """Render vector SVG to tinted QPixmap with High-DPI anti-aliasing."""
        cache_key = (icon_name, size, size, color)
        if cache_key in cls._pixmap_cache:
            return cls._pixmap_cache[cache_key]

        renderer = cls._get_renderer(icon_name)
        if not renderer:
            # Fallback blank pixmap
            pix = QPixmap(size, size)
            pix.fill(Qt.transparent)
            return pix

        # Render at 2x resolution for crisp High-DPI rendering
        scale = 2
        w = size * scale
        h = size * scale

        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter, QRectF(0, 0, w, h))

        # Tint with requested color using SourceIn composition
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(QRectF(0, 0, w, h), QColor(color))
        painter.end()

        pix.setDevicePixelRatio(scale)
        cls._pixmap_cache[cache_key] = pix
        return pix

    @classmethod
    def get_icon(cls, icon_name: str, size: int = 16, color: str = "#FFFFFF") -> QIcon:
        """Return QIcon from tinted vector SVG."""
        return QIcon(cls.get_pixmap(icon_name, size, color))


def get_svg_icon(name: str, size: int = 16, color: str = "#FFFFFF") -> QIcon:
    return SvgIconManager.get_icon(name, size, color)

def get_svg_pixmap(name: str, size: int = 16, color: str = "#FFFFFF") -> QPixmap:
    return SvgIconManager.get_pixmap(name, size, color)
