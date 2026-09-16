"""Confirm the Recovery store resolves through Qt's application-data location.

The location must never be hardcoded, mirroring
`test_category_template_settings`'s confirmation for the Category template.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QStandardPaths  # noqa: E402

from analysis import RecoverySnapshotStore  # noqa: E402
from recovery_settings import installation_recovery_store  # noqa: E402


def test_the_store_lives_under_qts_application_data_location(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        lambda location: (
            str(tmp_path) if location == QStandardPaths.StandardLocation.AppDataLocation else ""
        ),
    )

    store = installation_recovery_store()

    assert isinstance(store, RecoverySnapshotStore)
    assert store.path.parent == tmp_path / "recovery"
    # A fresh installation has never written one yet.
    assert store.read() is None


def test_a_missing_application_data_location_is_reported_rather_than_guessed(
    monkeypatch,
) -> None:
    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda location: "")

    with pytest.raises(OSError):
        installation_recovery_store()
