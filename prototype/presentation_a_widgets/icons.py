"""THROWAWAY PROTOTYPE A -- one SVG icon family, recoloured by state.

Lucide (ISC licence), 24x24 grid, stroke 1.75, round caps and joins, as the
tokens require. The geometry is held as SVG source so a single renderer can
recolour it per state and rasterise it at the device pixel ratio, which is the
thing the retired SF Symbols PNG exports could not do.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import tokens

_BODIES: dict[str, str] = {
    "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
    "pause": '<rect x="14" y="4" width="4" height="16" rx="1"/>'
    '<rect x="6" y="4" width="4" height="16" rx="1"/>',
    "step-back": '<line x1="18" y1="20" x2="18" y2="4"/>'
    '<polygon points="14 20 4 12 14 4"/>',
    "step-forward": '<line x1="6" y1="4" x2="6" y2="20"/>'
    '<polygon points="10 4 20 12 10 20"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
    '<path d="M3 3v5h5"/>',
    "rotate-cw": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>'
    '<path d="M21 3v5h-5"/>',
    "volume": '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
    '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>'
    '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>',
    "volume-x": '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
    '<line x1="22" y1="9" x2="16" y2="15"/>'
    '<line x1="16" y1="9" x2="22" y2="15"/>',
    "folder-open": '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5'
    'l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9'
    'l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>',
    "save": '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2'
    'H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>'
    '<path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/>'
    '<path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
    "file-plus": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M12 18v-6"/>',
    "film": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/>'
    '<path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/>'
    '<path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
    "video": '<path d="m22 8-6 4 6 4V8Z"/>'
    '<rect width="14" height="12" x="2" y="6" rx="2"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><path d="M8.12 8.12 12 12"/>'
    '<path d="M20 4 8.12 15.88"/><circle cx="6" cy="18" r="3"/>'
    '<path d="M14.8 14.8 20 20"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
    '<polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "trash": '<path d="M3 6h18"/>'
    '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
    '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
    '<line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "panel-left": '<rect width="18" height="18" x="3" y="3" rx="2"/>'
    '<path d="M9 3v18"/><path d="m16 15-3-3 3-3"/>',
    "maximize": '<path d="M8 3H5a2 2 0 0 0-2 2v3"/>'
    '<path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/>'
    '<path d="M16 21h3a2 2 0 0 0 2-2v-3"/>',
    "tag": '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172'
    'a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58'
    'a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r="1.1"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
}

_DOCUMENT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
    'stroke-linejoin="round">{body}</svg>'
)


def names() -> tuple[str, ...]:
    return tuple(sorted(_BODIES))


@lru_cache(maxsize=512)
def pixmap(name: str, color: str, size: int, ratio: float = 2.0) -> QPixmap:
    body = _BODIES[name]
    source = _DOCUMENT.format(color=color, stroke=tokens.ICON_STROKE, body=body)
    renderer = QSvgRenderer(source.encode("utf-8"))
    rendered = QPixmap(int(size * ratio), int(size * ratio))
    rendered.fill(Qt.transparent)
    painter = QPainter(rendered)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size * ratio, size * ratio))
    painter.end()
    rendered.setDevicePixelRatio(ratio)
    return rendered


@lru_cache(maxsize=512)
def icon(
    name: str,
    color: str = tokens.TEXT,
    size: int = tokens.ICON_SIZE_DEFAULT,
    disabled_color: str = tokens.TEXT_FAINT,
) -> QIcon:
    """One icon carrying its own normal and disabled colours."""
    built = QIcon()
    built.addPixmap(pixmap(name, color, size), QIcon.Normal)
    built.addPixmap(pixmap(name, disabled_color, size), QIcon.Disabled)
    return built


def tinted(name: str, color: QColor | str, size: int) -> QPixmap:
    return pixmap(name, QColor(color).name(), size)
