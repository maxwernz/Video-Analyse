"""Qt-owned location of the installation Recovery snapshot store."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths

from analysis import RecoverySnapshotStore


def installation_recovery_store() -> RecoverySnapshotStore:
    """Keep unsaved-work Recovery data with application state on every OS.

    A Recovery snapshot is installation-local durable state, never part of
    any Analysis file: it belongs beside other data this installation keeps
    for itself, not beside whatever file an analyst is editing. That is
    `AppDataLocation` rather than `AppConfigLocation` — the location
    `category_template_settings.installation_category_template_store` uses
    for the Category template, which is a setting an analyst can reasonably
    expect to find and edit. A Recovery snapshot is exactly the opposite: an
    analyst is never meant to go looking for it, only to be asked about it.
    """

    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not location:
        raise OSError("Qt did not provide an application data location")
    return RecoverySnapshotStore(Path(location) / "recovery")
