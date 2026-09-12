"""Where the application finds the resources it was packaged with.

A macOS application bundle keeps code in `Contents/Frameworks` and bundled data
in `Contents/Resources`, so a path built from a module's own location lands in
the wrong half of the bundle. One helper decides this for every module.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from app_runtime import overlay_font_path, resource_path, resource_root  # noqa: E402


PROJECT_ROOT = Path(__file__).parents[1]


def test_a_development_checkout_resolves_resources_against_the_project() -> None:
    assert resource_root() == PROJECT_ROOT
    assert resource_path("assets/fonts") == PROJECT_ROOT / "assets" / "fonts"
    assert overlay_font_path().is_file()


def test_a_macos_bundle_resolves_resources_beside_the_bundled_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = tmp_path / "Video Analyse.app" / "Contents"
    (contents / "Frameworks").mkdir(parents=True)
    (contents / "Resources").mkdir()
    monkeypatch.setattr(sys, "_MEIPASS", str(contents / "Frameworks"), raising=False)

    assert resource_root() == contents / "Resources"


def test_any_other_packaged_layout_resolves_resources_beside_the_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Windows one-directory layout puts code and data in one place."""

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resource_root() == tmp_path
    assert resource_path("qml/Main.qml") == tmp_path / "qml" / "Main.qml"


def test_a_bundle_without_a_resources_directory_falls_back_to_its_code_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frameworks = tmp_path / "Contents" / "Frameworks"
    frameworks.mkdir(parents=True)
    monkeypatch.setattr(sys, "_MEIPASS", str(frameworks), raising=False)

    assert resource_root() == frameworks
