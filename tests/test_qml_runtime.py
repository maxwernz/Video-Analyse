"""Getting a Qt Quick scene on screen on a machine nobody manages.

Qt Quick renders through a graphics backend — Direct3D 11 on Windows — where
Qt Widgets rasterises on the CPU. Video Analyse is delivered to unmanaged
devices whose graphics drivers nobody controls, so a backend that cannot
initialise must degrade to slow software rendering rather than to a crash.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from qml_runtime import (  # noqa: E402
    QmlSceneError,
    SceneGraphUnavailable,
    quick_scene_path,
    show_quick_scene_with_fallback,
    software_rendering_requested,
)


def test_the_bundled_scene_is_resolved_through_the_one_resource_root() -> None:
    assert quick_scene_path() == Path(__file__).parents[1] / "qml" / "Main.qml"
    assert quick_scene_path().is_file()


def test_a_scene_that_renders_is_shown_on_the_default_backend() -> None:
    attempts: list[str] = []
    software: list[str] = []

    scene = show_quick_scene_with_fallback(
        show=lambda: attempts.append("shown") or "scene",
        select_software=lambda: software.append("software"),
    )

    assert scene == "scene"
    assert attempts == ["shown"]
    assert software == []


def test_a_backend_that_cannot_initialise_is_retried_in_software() -> None:
    attempts: list[str] = []
    software: list[str] = []

    def show() -> str:
        attempts.append("shown")
        if len(attempts) == 1:
            raise SceneGraphUnavailable("no graphics device")
        return "scene"

    scene = show_quick_scene_with_fallback(
        show=show, select_software=lambda: software.append("software")
    )

    assert scene == "scene"
    assert attempts == ["shown", "shown"]
    assert software == ["software"], "software rendering was never selected"


def test_a_failure_that_survives_software_rendering_is_reported() -> None:
    software: list[str] = []

    def show() -> str:
        raise SceneGraphUnavailable("no graphics device")

    with pytest.raises(SceneGraphUnavailable):
        show_quick_scene_with_fallback(
            show=show, select_software=lambda: software.append("software")
        )

    assert software == ["software"], "the fallback was never attempted"


def test_a_scene_that_fails_to_load_is_not_blamed_on_the_graphics_backend() -> None:
    attempts: list[str] = []
    software: list[str] = []

    def show() -> str:
        attempts.append("shown")
        raise QmlSceneError("Main.qml: Cannot assign to non-existent property")

    with pytest.raises(QmlSceneError):
        show_quick_scene_with_fallback(
            show=show, select_software=lambda: software.append("software")
        )

    assert attempts == ["shown"], "a broken scene was pointlessly loaded twice"
    assert software == []


def test_software_rendering_can_be_demanded_before_any_detection() -> None:
    """The escape hatch for a driver that crashes instead of reporting."""

    assert software_rendering_requested({}) is False
    assert software_rendering_requested({"VIDEO_ANALYSE_SOFTWARE_RENDERING": ""}) is False
    assert software_rendering_requested({"VIDEO_ANALYSE_SOFTWARE_RENDERING": "1"}) is True
