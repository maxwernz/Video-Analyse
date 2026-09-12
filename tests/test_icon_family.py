"""The vendored Lucide family, and recolouring one source file per state."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QIcon, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import icon_family  # noqa: E402


@pytest.fixture(scope="module")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


def opaque_pixels(image: QImage) -> list[QColor]:
    """The fully painted pixels. Antialiased edges are blends of the icon
    colour with transparency, so only the solid interior of a stroke states the
    colour exactly."""
    unpremultiplied = image.convertToFormat(QImage.Format.Format_ARGB32)
    return [
        unpremultiplied.pixelColor(x, y)
        for y in range(unpremultiplied.height())
        for x in range(unpremultiplied.width())
        if unpremultiplied.pixelColor(x, y).alpha() == 255
    ]


def painted_pixels(image: QImage) -> int:
    """Every pixel the renderer touched, edges included."""
    unpremultiplied = image.convertToFormat(QImage.Format.Format_ARGB32)
    return sum(
        unpremultiplied.pixelColor(x, y).alpha() > 0
        for y in range(unpremultiplied.height())
        for x in range(unpremultiplied.width())
    )


def test_every_icon_the_interface_names_is_vendored() -> None:
    vendored = set(icon_family.available_icons())

    assert set(icon_family.ICON_NAMES) <= vendored
    assert vendored == set(icon_family.ICON_NAMES)


def test_the_lucide_licence_travels_with_the_icons() -> None:
    licence = icon_family.LICENCE_PATH.read_text(encoding="utf-8")

    assert icon_family.LICENCE_PATH.is_file()
    assert "ISC License" in licence
    assert "Lucide Icons and Contributors" in licence


@pytest.mark.parametrize("name", sorted(icon_family.ICON_NAMES))
def test_vendored_icons_are_upstream_lucide_rather_than_transcriptions(
    name: str,
) -> None:
    """A hand-drawn copy has neither the upstream licence stamp nor
    ``currentColor``; requiring both keeps transcriptions out of production."""
    document = (icon_family.ICON_DIRECTORY / f"{name}.svg").read_text(
        encoding="utf-8"
    )

    assert "lucide-static" in document
    assert 'stroke="currentColor"' in document


def test_an_icon_renders_in_two_colours_from_one_source_file(
    application: QApplication,
) -> None:
    accent = icon_family.render_icon("play", "#E4306B", size=20)
    muted = icon_family.render_icon("play", "#8A9099", size=20)

    assert accent != muted
    assert {colour.name() for colour in opaque_pixels(accent)} == {"#e4306b"}
    assert {colour.name() for colour in opaque_pixels(muted)} == {"#8a9099"}


def test_an_icon_renders_at_the_device_pixel_ratio(
    application: QApplication,
) -> None:
    image = icon_family.render_icon(
        "play", "#E8EAED", size=20, device_pixel_ratio=2.0
    )

    assert image.width() == 40
    assert image.height() == 40
    assert image.devicePixelRatio() == 2.0


def test_icons_are_drawn_at_the_token_stroke_weight(
    application: QApplication,
) -> None:
    """1.75 is a token, not a drawing detail, and upstream Lucide ships 2."""
    token_weight = icon_family.render_icon("film", "#E8EAED")
    upstream_weight = icon_family.render_icon(
        "film", "#E8EAED", stroke_width=2.0
    )

    assert icon_family.STROKE_WIDTH == 1.75
    assert painted_pixels(token_weight) < painted_pixels(upstream_weight)


def test_an_icon_that_was_never_vendored_is_an_error(
    application: QApplication,
) -> None:
    with pytest.raises(KeyError):
        icon_family.render_icon("teleporter", "#E8EAED")


def test_a_state_icon_gives_each_state_its_own_colour(
    application: QApplication,
) -> None:
    icon = icon_family.state_icon(
        "play",
        idle="#8A9099",
        hover="#E8EAED",
        active="#E4306B",
        disabled="#5E646C",
        size=20,
    )

    idle = icon.pixmap(20, 20, QIcon.Mode.Normal, QIcon.State.Off).toImage()
    hover = icon.pixmap(20, 20, QIcon.Mode.Active, QIcon.State.Off).toImage()
    active = icon.pixmap(20, 20, QIcon.Mode.Normal, QIcon.State.On).toImage()
    disabled = icon.pixmap(20, 20, QIcon.Mode.Disabled, QIcon.State.Off).toImage()

    assert {colour.name() for colour in opaque_pixels(idle)} == {"#8a9099"}
    assert {colour.name() for colour in opaque_pixels(hover)} == {"#e8eaed"}
    assert {colour.name() for colour in opaque_pixels(active)} == {"#e4306b"}
    assert {colour.name() for colour in opaque_pixels(disabled)} == {"#5e646c"}


def test_a_state_icon_falls_back_to_the_idle_colour(
    application: QApplication,
) -> None:
    icon = icon_family.state_icon("play", idle="#8A9099", size=20)

    hover = icon.pixmap(20, 20, QIcon.Mode.Active, QIcon.State.Off).toImage()

    assert {colour.name() for colour in opaque_pixels(hover)} == {"#8a9099"}
