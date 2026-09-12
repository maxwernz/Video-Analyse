"""THROWAWAY PROTOTYPE A -- resolving the two token families.

The tokens call for bundled Inter and JetBrains Mono in ``assets/fonts/``.
Neither is actually in the repository yet (only ``NotoSans.ttf`` is), so this
resolves the nearest available family and records what it had to substitute.
The substitution is reported in FINDINGS.md rather than hidden.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from . import tokens

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_FONT_DIRECTORY = REPOSITORY_ROOT / "assets" / "fonts"

SUBSTITUTIONS: list[str] = []

_ui_family = "Noto Sans"
_mono_family = "Menlo"


def load() -> None:
    """Register bundled faces and pick the closest family for each role."""
    global _ui_family, _mono_family

    for font_file in sorted(BUNDLED_FONT_DIRECTORY.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font_file))
    for font_file in sorted((Path(__file__).parent / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font_file))

    families = set(QFontDatabase.families())

    _ui_family = _first_available(
        families,
        ["Inter", "Inter Display", "Noto Sans", "Helvetica Neue", "Arial"],
    )
    if _ui_family != "Inter":
        SUBSTITUTIONS.append(
            f"UI family: tokens ask for Inter, bundled font missing, using {_ui_family}"
        )

    _mono_family = _first_available(
        families,
        ["JetBrains Mono", "SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono"],
    )
    if _mono_family != "JetBrains Mono":
        SUBSTITUTIONS.append(
            "Timecode family: tokens ask for JetBrains Mono, bundled font missing, "
            f"using {_mono_family}"
        )


def _first_available(families: set[str], candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate in families:
            return candidate
    return candidates[-1]


def ui(size: int = tokens.SIZE_BODY, weight: int = tokens.WEIGHT_REGULAR) -> QFont:
    font = QFont(_ui_family)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    font.setLetterSpacing(QFont.PercentageSpacing, 100.0)
    return font


def mono(size: int = tokens.SIZE_TIMECODE, weight: int = tokens.WEIGHT_MEDIUM) -> QFont:
    """A timecode face. Tabular figures, so columns of digits align optically."""
    font = QFont(_mono_family)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    font.setStyleHint(QFont.Monospace)
    font.setFixedPitch(True)
    return font


def ui_family() -> str:
    return _ui_family


def mono_family() -> str:
    return _mono_family
