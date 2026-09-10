from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from uuid import UUID

from PySide6.QtCore import QTime, Signal
from PySide6.QtWidgets import QWidget

from Ui_clip_handler import Ui_Dialog
from treewidget_item import ClipItem
from util import milliseconds_to_hhmmss


@dataclass(frozen=True)
class ClipDraft:
    """What the user entered about a Clip, before the Analysis accepts it."""

    name: str
    notes: str
    category_name: str | None
    start_ms: int
    end_ms: int
    clip_id: UUID | None = None


class ClipHandler(QWidget, Ui_Dialog):
    """Collects Clip details; the Analysis decides what becomes of them."""

    clip_submitted = Signal(object)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi(self)

        self.start_ms = 0
        self.end_ms = 0

        self.clipNameLine.textChanged.connect(
            lambda text: self.acceptButton.setEnabled(bool(text.strip()))
        )
        self.startTimeEdit.timeChanged.connect(self._set_duration_label)
        self.endTimeEdit.timeChanged.connect(self._set_duration_label)
        self.acceptButton.clicked.connect(self._submit)

    @property
    def start_ms(self) -> int:
        """The Clip start; the boundary fields are where the form keeps it."""
        return self.startTimeEdit.time().msecsSinceStartOfDay()

    @start_ms.setter
    def start_ms(self, milliseconds: int) -> None:
        self.startTimeEdit.setTime(QTime.fromMSecsSinceStartOfDay(milliseconds))

    @property
    def end_ms(self) -> int:
        """The Clip end; likewise editable, and likewise the Analysis's to judge."""
        return self.endTimeEdit.time().msecsSinceStartOfDay()

    @end_ms.setter
    def end_ms(self, milliseconds: int) -> None:
        self.endTimeEdit.setTime(QTime.fromMSecsSinceStartOfDay(milliseconds))

    def set_categories(
        self,
        category_names: Iterable[str],
        selected: str | None = None,
    ) -> None:
        self.categoryBox.clear()
        self.categoryBox.addItems(list(category_names))
        self.categoryBox.setCurrentText("" if selected is None else selected)

    def current_category_name(self) -> str | None:
        category = self.categoryBox.currentText().strip()
        return category or None

    def _set_duration_label(self) -> None:
        """How long the Clip is; the boundaries themselves are their own fields."""
        length = max(self.end_ms - self.start_ms, 0)
        self.clipDuration.setText(milliseconds_to_hhmmss(length))

    def _draft(self) -> ClipDraft:
        return ClipDraft(
            name=self.clipNameLine.text().strip(),
            notes=self.notesText.toPlainText(),
            category_name=self.current_category_name(),
            start_ms=self.start_ms,
            end_ms=self.end_ms,
        )

    def _submit(self) -> None:
        self.clip_submitted.emit(self._draft())


class CreateClip(ClipHandler):
    """Turns a Pending Clip into a draft the Analysis can accept."""

    def __init__(self, parent=None):
        ClipHandler.__init__(self, parent)
        self.last_category: str | None = None

    def new_clip(
        self,
        clip_start: int,
        clip_stop: int,
        category_names: Iterable[str] = (),
    ) -> None:
        self.start_ms = clip_start
        self.end_ms = clip_stop

        self.clipNameLine.setText("")
        self.notesText.setText("")
        category_names = list(category_names)
        selected = (
            self.last_category if self.last_category in category_names else None
        )
        self.set_categories(category_names, selected)
        self._set_duration_label()

        self.acceptButton.setDisabled(True)

    def _submit(self) -> None:
        self.last_category = self.current_category_name()
        super()._submit()


class EditClip(ClipHandler):
    """Edits an existing Clip, identified by its Analysis identity."""

    def __init__(self, parent=None):
        ClipHandler.__init__(self, parent)
        self.clip_id: UUID | None = None

    def new_clip(
        self,
        clip_item: ClipItem,
        category_names: Iterable[str] = (),
    ) -> None:
        self.clip_id = clip_item.clip_id
        self.start_ms, self.end_ms = clip_item.clip_times()
        self._set_duration_label()

        self.clipNameLine.setText(clip_item.name)
        self.notesText.setText(clip_item.notes)
        self.set_categories(category_names, clip_item.category)
        self.acceptButton.setEnabled(bool(clip_item.name.strip()))

    def _draft(self) -> ClipDraft:
        return replace(super()._draft(), clip_id=self.clip_id)
