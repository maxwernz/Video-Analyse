"""Renders the Source videos of an Analysis, and reports which one to show.

This is the Videos tab of the sidebar. It owns no durable state: it renders
whatever Analysis it is given and reports a chosen Source video by identity,
leaving the switching to the window, which activates it through the one
navigation seam the workspace has.
"""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QListWidget, QListWidgetItem

from analysis import Analysis, SourceVideo


class SourceVideoItem(QListWidgetItem):
    """One row naming a Source video of the Analysis."""

    def __init__(self, source_video: SourceVideo, parent=None):
        QListWidgetItem.__init__(self, parent)
        self.source_video_id = source_video.id
        self.setText(source_video.display_name)
        self.setToolTip(source_video.location)


class SourceVideoList(QListWidget):
    """The Source-video selector of the sidebar's Videos tab."""

    source_video_activated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.itemClicked.connect(self._request_activation)
        self.itemActivated.connect(self._request_activation)

    def render_analysis(
        self,
        analysis: Analysis,
        active_source_video_id: UUID | None = None,
    ) -> None:
        """Rebuild the list, marking the Active Source video as the chosen row."""
        self.clear()
        for source_video in analysis.source_videos:
            item = SourceVideoItem(source_video, parent=self)
            if source_video.id == active_source_video_id:
                self.setCurrentItem(item)

    def _request_activation(self, item: QListWidgetItem) -> None:
        """Report the chosen Source video by identity; the window switches to it."""
        if isinstance(item, SourceVideoItem):
            self.source_video_activated.emit(item.source_video_id)
