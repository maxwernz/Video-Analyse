"""Serve the vendored icon family to QML, recoloured on demand.

`icon_family.py` already owns the hard part: one Lucide SVG per icon, the token
stroke weight substituted in, the requested colour substituted for
``currentColor``, rendered at a device pixel ratio and cached. What QML needs on
top of that is an address it can put in an `Image.source`, which is what a
`QQuickImageProvider` is for. So this module is a seam and not a second
renderer: it parses the URL, asks `icon_family` for the image, and hands it
back.

QML asks for ``image://icon/play?color=%23E8EAED``; `Theme.qml` builds that
address in one function, so no component ever spells the scheme itself.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

import icon_family


#: The scheme QML addresses the family through: `image://icon/<name>`.
PROVIDER_NAME = "icon"

#: The colour an address without one gets. Naming a colour is the caller's job
#: — this exists so a mistake renders a visible icon rather than nothing.
DEFAULT_COLOR = "#E8EAED"


class IconProvider(QQuickImageProvider):
    """`image://icon/<name>?color=%23E8EAED` — one SVG, any colour."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(  # noqa: N802 - Qt override
        self,
        identifier: str,
        size: QSize,
        requested: QSize,
    ) -> QImage:
        name, _, query = identifier.partition("?")
        colors = parse_qs(query).get("color")
        color = colors[0] if colors and colors[0] else DEFAULT_COLOR

        extent = max(
            requested.width(),
            requested.height(),
            0,
        ) or icon_family.DEFAULT_SIZE

        try:
            image = icon_family.render_icon(name, color, extent)
        except KeyError:
            # An icon nobody vendored is a mistake in the QML, and returning a
            # null image is how the engine gets told: it logs a warning, and
            # `tests/test_qml_workspace.py` treats engine warnings as failures.
            return QImage()

        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


def install_icon_provider(engine: QQmlApplicationEngine) -> None:
    """Give a QML engine the icon family."""

    engine.addImageProvider(PROVIDER_NAME, IconProvider())
