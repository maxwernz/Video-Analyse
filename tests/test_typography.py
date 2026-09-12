from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app_runtime import (  # noqa: E402
    BUNDLED_FONT_FILES,
    TIMECODE_FONT_FAMILY,
    UI_FONT_FAMILY,
    FontRegistrationError,
    bundled_font_paths,
    register_bundled_fonts,
)


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_both_bundled_families_are_available_after_registration(
    application: QApplication,
) -> None:
    register_bundled_fonts()

    families = set(QFontDatabase.families())
    assert UI_FONT_FAMILY in families
    assert TIMECODE_FONT_FAMILY in families


def test_every_bundled_font_file_ships_with_the_application() -> None:
    for path in bundled_font_paths():
        assert path.is_file(), f"the bundled font {path.name} is missing"

    licences = Path(bundled_font_paths()[0]).parent
    assert (licences / "OFL-Inter.txt").is_file()
    assert (licences / "OFL-JetBrainsMono.txt").is_file()


def test_a_missing_font_file_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    import app_runtime

    monkeypatch.setattr(
        app_runtime,
        "bundled_font_paths",
        lambda: [Path("nowhere") / BUNDLED_FONT_FILES[0]],
    )

    with pytest.raises(FontRegistrationError):
        app_runtime.register_bundled_fonts()


def test_an_unreadable_font_file_fails_loudly(
    application: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import app_runtime

    not_a_font = tmp_path / BUNDLED_FONT_FILES[0]
    not_a_font.write_bytes(b"this is not a font")
    monkeypatch.setattr(app_runtime, "bundled_font_paths", lambda: [not_a_font])

    with pytest.raises(FontRegistrationError):
        app_runtime.register_bundled_fonts()


def test_a_family_that_never_arrives_fails_loudly(
    application: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app_runtime

    monkeypatch.setattr(
        app_runtime,
        "REQUIRED_FONT_FAMILIES",
        ("A Family No Font Provides",),
    )

    with pytest.raises(FontRegistrationError):
        app_runtime.register_bundled_fonts()


def test_startup_makes_both_families_available(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")

    result = subprocess.run(
        [sys.executable, "main.py", "--smoke-test"],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["fonts"] == [UI_FONT_FAMILY, TIMECODE_FONT_FAMILY]
