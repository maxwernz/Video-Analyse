from __future__ import annotations

import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QAbstractSpinBox


_DURATION_PATTERN = re.compile(
    r"^(?P<hours>\d+):(?P<minutes>[0-5]\d):(?P<seconds>[0-5]\d)"
    r"(?:\.(?P<milliseconds>\d{1,3}))?$"
)


def _format_duration(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _parse_duration(text: str) -> int | None:
    match = _DURATION_PATTERN.fullmatch(text.strip())
    if match is None:
        return None
    milliseconds = (match.group("milliseconds") or "0").ljust(3, "0")
    return (
        int(match.group("hours")) * 3_600_000
        + int(match.group("minutes")) * 60_000
        + int(match.group("seconds")) * 1_000
        + int(milliseconds)
    )


class DurationEdit(QAbstractSpinBox):
    """Edits a non-negative media duration without a 24-hour clock limit."""

    millisecondsChanged = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._milliseconds = 0
        self.setAccelerated(True)
        self.editingFinished.connect(self._commit_text)
        self._render_value()

    def milliseconds(self) -> int:
        return self._milliseconds

    def setMilliseconds(self, milliseconds: int) -> None:
        if milliseconds < 0:
            raise ValueError("A duration cannot be negative")
        if milliseconds == self._milliseconds:
            self._render_value()
            return
        self._milliseconds = milliseconds
        self._render_value()
        self.millisecondsChanged.emit(milliseconds)

    def stepBy(self, steps: int) -> None:
        self.setMilliseconds(max(0, self._milliseconds + steps * 1_000))

    def stepEnabled(self):
        enabled = QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
        if self._milliseconds > 0:
            enabled |= QAbstractSpinBox.StepEnabledFlag.StepDownEnabled
        return enabled

    def validate(self, text: str, position: int):
        if _parse_duration(text) is not None:
            state = QValidator.State.Acceptable
        elif re.fullmatch(r"\d*(?::[0-5]?\d?)?(?::[0-5]?\d?)?(?:\.\d{0,3})?", text):
            state = QValidator.State.Intermediate
        else:
            state = QValidator.State.Invalid
        return state, text, position

    def _commit_text(self) -> None:
        milliseconds = _parse_duration(self.lineEdit().text())
        if milliseconds is None:
            self._render_value()
            return
        self.setMilliseconds(milliseconds)

    def _render_value(self) -> None:
        self.lineEdit().setText(_format_duration(self._milliseconds))

