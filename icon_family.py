"""One icon family, one stroke weight, any colour.

Every icon in Video Analyse comes from `Lucide <https://lucide.dev>`_ (ISC),
vendored as its real upstream SVGs under ``assets/icons/lucide/`` with the
licence text beside them. The files are byte-identical to ``lucide-static``, so
re-vendoring a newer release is a copy rather than a merge, and a hand-drawn
approximation cannot pass for one of them.

Upstream ships each icon once, painted in ``currentColor`` at stroke weight 2.
Qt's SVG renderer has no equivalent of ``currentColor`` and no way to override a
stroke, so an icon that changes with its control's state is either duplicated
once per colour per state on disk or rewritten on the way to the renderer. This
module rewrites: it substitutes the requested colour and the token stroke weight
into the source document, renders at the device pixel ratio the caller asks for,
and caches the result. One file per icon, any number of colours.

``docs/design/visual-tokens.md`` owns the numbers this module restates: stroke
1.75, 20px in the transport and 16px everywhere else. It does not own the state
colours -- callers pass those in, so this module never becomes a second, drifting
copy of the palette.
"""

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from app_runtime import resource_path


ICON_DIRECTORY = resource_path("assets/icons/lucide")
LICENCE_PATH = ICON_DIRECTORY / "LICENSE"

#: The token stroke weight. Upstream Lucide draws at 2.
STROKE_WIDTH = 1.75

#: Icon sizes the visual system names, in logical pixels.
TRANSPORT_SIZE = 20
DEFAULT_SIZE = 16

#: The icons the interface draws from, by their upstream Lucide names. Adding a
#: name here without vendoring its file fails a test rather than rendering
#: nothing.
ICON_NAMES: tuple[str, ...] = (
    "check",
    "chevron-down",
    "chevron-right",
    "circle-dot",
    "file-plus",
    "file-video",
    "film",
    "folder-open",
    "grip",
    "maximize",
    "panel-left",
    "pause",
    "pencil",
    "play",
    "plus",
    "rotate-ccw",
    "rotate-cw",
    "save",
    "search",
    "square",
    "step-back",
    "step-forward",
    "trash-2",
    "triangle-alert",
    "upload",
    "volume-2",
    "volume-x",
    "x",
)

_CURRENT_COLOR = re.compile(r'"currentColor"')
_STROKE_WIDTH = re.compile(r'stroke-width="[0-9.]+"')

_sources: dict[str, str] = {}
_rendered: dict[tuple[str, str, int, float, float], QImage] = {}


def available_icons() -> tuple[str, ...]:
    """The icon names actually present on disk."""
    return tuple(sorted(path.stem for path in ICON_DIRECTORY.glob("*.svg")))


def _source_document(name: str) -> str:
    cached = _sources.get(name)
    if cached is not None:
        return cached
    path = ICON_DIRECTORY / f"{name}.svg"
    if not path.is_file():
        raise KeyError(f"No Lucide icon named {name!r} is vendored")
    document = path.read_text(encoding="utf-8")
    _sources[name] = document
    return document


def render_icon(
    name: str,
    color: str,
    size: int = DEFAULT_SIZE,
    *,
    device_pixel_ratio: float = 1.0,
    stroke_width: float = STROKE_WIDTH,
) -> QImage:
    """Render one vendored icon in ``color`` at ``size`` logical pixels.

    The returned image is ``size * device_pixel_ratio`` device pixels square and
    carries that ratio, so Qt draws it at its logical size and it stays crisp on
    a high-resolution display.

    Raises ``KeyError`` if the icon was never vendored.
    """
    key = (name, color, size, device_pixel_ratio, stroke_width)
    cached = _rendered.get(key)
    if cached is not None:
        return cached

    document = _source_document(name)
    document = _CURRENT_COLOR.sub(f'"{color}"', document)
    document = _STROKE_WIDTH.sub(f'stroke-width="{stroke_width}"', document)

    extent = max(1, round(size * device_pixel_ratio))
    image = QImage(extent, extent, QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(device_pixel_ratio)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(document.encode("utf-8")).render(painter)
    painter.end()

    _rendered[key] = image
    return image


def icon_pixmap(
    name: str,
    color: str,
    size: int = DEFAULT_SIZE,
    *,
    device_pixel_ratio: float = 1.0,
    stroke_width: float = STROKE_WIDTH,
) -> QPixmap:
    """``render_icon`` as a pixmap, for the widget APIs that want one."""
    return QPixmap.fromImage(
        render_icon(
            name,
            color,
            size,
            device_pixel_ratio=device_pixel_ratio,
            stroke_width=stroke_width,
        )
    )


def state_icon(
    name: str,
    *,
    idle: str,
    hover: str | None = None,
    active: str | None = None,
    disabled: str | None = None,
    size: int = DEFAULT_SIZE,
    device_pixel_ratio: float = 1.0,
) -> QIcon:
    """One ``QIcon`` carrying a separately coloured pixmap for each state.

    Qt asks for ``Active`` when a control is hovered, ``State.On`` when it is
    toggled on, and ``Disabled`` when it cannot be pressed. Any state left
    unspecified falls back to ``idle``, so a control that only ever has one
    appearance says so in one argument.
    """
    hover = hover or idle
    active = active or idle
    disabled = disabled or idle

    icon = QIcon()
    for colour, mode, state in (
        (idle, QIcon.Mode.Normal, QIcon.State.Off),
        (hover, QIcon.Mode.Active, QIcon.State.Off),
        (hover, QIcon.Mode.Selected, QIcon.State.Off),
        (active, QIcon.Mode.Normal, QIcon.State.On),
        (active, QIcon.Mode.Active, QIcon.State.On),
        (active, QIcon.Mode.Selected, QIcon.State.On),
        (disabled, QIcon.Mode.Disabled, QIcon.State.Off),
        (disabled, QIcon.Mode.Disabled, QIcon.State.On),
    ):
        icon.addPixmap(
            icon_pixmap(
                name,
                colour,
                size,
                device_pixel_ratio=device_pixel_ratio,
            ),
            mode,
            state,
        )
    return icon
