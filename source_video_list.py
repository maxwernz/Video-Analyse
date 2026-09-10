"""Renders the Source videos of an Analysis, and reports which one to show.

This is the Videos tab of the sidebar. It owns no durable state: it renders
whatever Analysis it is given and reports a chosen Source video by identity,
leaving the switching to the window, which activates it through the one
navigation seam the workspace has.
"""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QFrame, QListWidget, QListWidgetItem

from analysis import Analysis, SourceVideo


class SourceVideoItem(QListWidgetItem):
    """One row naming a Source video of the Analysis."""

    def __init__(self, source_video: SourceVideo, parent=None):
        QListWidgetItem.__init__(self, parent)
        self.source_video_id = source_video.id
        self.setText(source_video.display_name)
        self.setToolTip(source_video.location)


def _rows_of(analysis: Analysis) -> tuple[tuple[UUID, str, str], ...]:
    """Everything the list draws, so an unchanged list can be left alone."""
    return tuple(
        (source_video.id, source_video.display_name, source_video.location)
        for source_video in analysis.source_videos
    )


class SourceVideoList(QListWidget):
    """The Source-video selector of the sidebar's Videos tab."""

    source_video_activated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._rows: tuple[tuple[UUID, str, str], ...] = ()
        self.currentItemChanged.connect(self.request_activation)

    def render_analysis(
        self,
        analysis: Analysis,
        active_source_video_id: UUID | None = None,
    ) -> None:
        """Draw the Source videos, and mark the Active Source video among them.

        The rows are rebuilt only when the Source videos themselves changed:
        activating one redraws the list from inside the very click that chose
        it, and rebuilding then would delete the row still being clicked.
        """
        rows = _rows_of(analysis)
        if rows != self._rows:
            self._rows = rows
            self.clear()
            for source_video in analysis.source_videos:
                SourceVideoItem(source_video, parent=self)
        self.show_active_source_video(active_source_video_id)

    def show_active_source_video(self, source_video_id: UUID | None) -> None:
        """Mark a Source video as chosen without asking to switch to it again."""
        chosen = next(
            (
                row
                for row, (identity, _name, _location) in enumerate(self._rows)
                if identity == source_video_id
            ),
            -1,
        )
        with QSignalBlocker(self):
            self.setCurrentRow(chosen)

    def request_activation(self, item: QListWidgetItem, _previous=None) -> None:
        """Report the chosen Source video by identity; the window switches to it."""
        if isinstance(item, SourceVideoItem):
            self.source_video_activated.emit(item.source_video_id)
