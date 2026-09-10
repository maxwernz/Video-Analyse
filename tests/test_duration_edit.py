from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from duration_edit import DurationEdit  # noqa: E402


def test_duration_edit_round_trips_positions_beyond_24_hours() -> None:
    application = QApplication.instance() or QApplication([])
    editor = DurationEdit()

    editor.setMilliseconds(90_000_123)

    assert editor.milliseconds() == 90_000_123
    assert editor.lineEdit().text() == "25:00:00.123"
    assert application is not None


def test_duration_edit_commits_a_typed_media_position() -> None:
    application = QApplication.instance() or QApplication([])
    editor = DurationEdit()
    editor.lineEdit().setText("48:01:02.003")

    editor.editingFinished.emit()

    assert editor.milliseconds() == 172_862_003
    assert application is not None
