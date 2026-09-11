"""Serve the icon family to QML, recoloured on demand.

Qt's SVG renderer has no ``currentColor``, so an icon that has to change with
its control's state is either duplicated once per colour or recoloured at load
time. Doing it in an image provider keeps one SVG per icon, renders at the
device pixel ratio the item actually asks for, and lets QML write
``source: "image://icon/play?color=" + Theme.textMuted`` and nothing else.

This is presentation work living in Python, and the prototype counts it as
such: it is roughly eighty lines, and it is the price of one icon family that
recolours cleanly on HiDPI.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

ICON_DIRECTORY = Path(__file__).resolve().parent / "qml" / "icons"
DEFAULT_SIZE = 16
_PLACEHOLDER = re.compile(r"#000000")


class IconProvider(QQuickImageProvider):
    """`image://icon/<name>?color=%23E8EAED` — one SVG, any colour."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._sources: dict[str, str] = {}
        self._rendered: dict[tuple[str, str, int, int], QImage] = {}

    def _source(self, name: str) -> str | None:
        if name not in self._sources:
            path = ICON_DIRECTORY / f"{name}.svg"
            if not path.is_file():
                return None
            self._sources[name] = path.read_text(encoding="utf-8")
        return self._sources[name]

    def requestImage(  # noqa: N802 - Qt override
        self,
        identifier: str,
        size: QSize,
        requested: QSize,
    ) -> QImage:
        name, _, query = identifier.partition("?")
        color = "#E8EAED"
        for part in query.split("&"):
            key, _, value = part.partition("=")
            if key == "color" and value:
                color = value.replace("%23", "#")

        width = requested.width() if requested.width() > 0 else DEFAULT_SIZE
        height = requested.height() if requested.height() > 0 else DEFAULT_SIZE
        key = (name, color, width, height)
        cached = self._rendered.get(key)
        if cached is not None:
            size.setWidth(cached.width())
            size.setHeight(cached.height())
            return cached

        document = self._source(name)
        if document is None:
            return QImage()
        renderer = QSvgRenderer(
            _PLACEHOLDER.sub(color, document).encode("utf-8")
        )
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(painter)
        painter.end()

        self._rendered[key] = image
        size.setWidth(width)
        size.setHeight(height)
        return image

    def known_icons(self) -> list[str]:
        return sorted(path.stem for path in ICON_DIRECTORY.glob("*.svg"))
