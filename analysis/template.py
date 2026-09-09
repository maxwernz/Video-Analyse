from __future__ import annotations

from collections.abc import Iterable

from .document import AnalysisDocument
from .model import Analysis

#: The installation-local starting Categories copied into a new Analysis.
DEFAULT_CATEGORY_TEMPLATE: tuple[tuple[str, str], ...] = (
    ("Abwehr", "#3B82F6"),
    ("Angriff", "#EF4444"),
    ("Tor", "#22C55E"),
)


def apply_category_template(
    analysis: Analysis,
    template: Iterable[tuple[str, str]] = DEFAULT_CATEGORY_TEMPLATE,
) -> None:
    """Copy a Category template into an Analysis, skipping names it already has."""
    for name, color in template:
        if analysis.category_named(name) is None:
            analysis.add_category(name, color)


def new_analysis_document(title: str = "") -> AnalysisDocument:
    """Create a clean, empty Analysis document seeded with the default template."""
    analysis = Analysis(title)
    apply_category_template(analysis)
    return AnalysisDocument(analysis)
