"""Fixtures shared by the whole suite.

Every test gets its own Category-template location, never the real
installation-local one `category_template_store.template_store_path`
resolves through `QStandardPaths`: `analysis.template.new_analysis_document`
reads that store by default, and `new_analysis_document()` with no explicit
template is called by tests across this suite, including the frozen
`test_main_window_workflow.py`. Leaving that pointed at this machine's real
application-data directory would make those tests depend on whatever this
suite (or a previous run of it) happened to leave there.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_category_template_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "VIDEO_ANALYSE_CATEGORY_TEMPLATE_PATH",
        str(tmp_path / "category-template.json"),
    )
