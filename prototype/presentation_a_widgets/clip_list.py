"""THROWAWAY PROTOTYPE A -- the Clip list and the Source-video list.

A ``QTreeView`` keeps the native structure -- grouping, expand and collapse,
keyboard navigation, an accessible selection model -- while a
``QStyledItemDelegate`` owns the whole row appearance. That is what "mostly
native Widgets" is supposed to mean: native behaviour, no stock look, and in
particular no column header, which is what truncated the Source-video column in
the shipped interface.
"""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
    QWidget,
)

from analysis.model import Analysis

from . import fixture, fonts, icons, tokens

KIND = Qt.UserRole + 1
COLOR = Qt.UserRole + 2
TITLE = Qt.UserRole + 3
START = Qt.UserRole + 4
DURATION = Qt.UserRole + 5
SOURCE_CUE = Qt.UserRole + 6
ENTITY_ID = Qt.UserRole + 7
COUNT = Qt.UserRole + 8

GROUP = "group"
CLIP = "clip"
SOURCE = "source"

BAR_WIDTH = 3
BAR_GAP = 11
RIGHT_PAD = 12
GROUP_ROW_HEIGHT = 30


class RowDelegate(QStyledItemDelegate):
    """Paints every row shape in the sidebar: Category headers, Clips, videos."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title_font = fonts.ui(tokens.SIZE_ROW_TITLE, tokens.WEIGHT_MEDIUM)
        self._section_font = fonts.ui(tokens.SIZE_SECTION_LABEL, tokens.WEIGHT_MEDIUM)
        self._body_font = fonts.ui(tokens.SIZE_BODY, tokens.WEIGHT_REGULAR)
        self._timecode_font = fonts.mono(tokens.SIZE_TIMECODE, tokens.WEIGHT_MEDIUM)
        self._cue_font = fonts.mono(tokens.SIZE_SECTION_LABEL, tokens.WEIGHT_REGULAR)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        if index.data(KIND) == GROUP:
            return QSize(0, GROUP_ROW_HEIGHT)
        return QSize(0, tokens.CLIP_ROW_HEIGHT)

    def paint(  # noqa: N802 - Qt naming
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        kind = index.data(KIND)
        if kind == GROUP:
            self._paint_group(painter, option, index)
        else:
            self._paint_row(painter, option, index)
        painter.restore()

    # ---------- Category header ----------

    def _paint_group(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        rect = option.rect
        painter.fillRect(rect, QColor(tokens.PANEL))

        color = QColor(index.data(COLOR) or tokens.TEXT_FAINT)
        chevron = "chevron-down" if option.state & QStyle.State_Open else "chevron-right"
        size = 12
        painter.drawPixmap(
            QRect(8, rect.center().y() - size // 2 + 1, size, size),
            icons.tinted(chevron, tokens.TEXT_FAINT, size),
        )

        # The Category cue is a colour bar, never coloured text: the shipped
        # interface tinted the group label itself, which is the failure marked
        # in the captures.
        bar = QRect(26, rect.center().y() - 5, BAR_WIDTH, 10)
        painter.fillRect(bar, color)

        painter.setFont(self._section_font)
        painter.setPen(QColor(tokens.TEXT_MUTED))
        text_left = bar.right() + 8
        painter.drawText(
            QRect(text_left, rect.top(), rect.width() - text_left, rect.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            str(index.data(TITLE) or ""),
        )

        count = index.data(COUNT)
        if count is not None:
            painter.setFont(self._cue_font)
            painter.setPen(QColor(tokens.TEXT_FAINT))
            painter.drawText(
                QRect(0, rect.top(), rect.width() - RIGHT_PAD, rect.height()),
                Qt.AlignVCenter | Qt.AlignRight,
                str(count),
            )

    # ---------- Clip and Source-video rows ----------

    def _paint_row(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        rect = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        if selected:
            painter.fillRect(rect, QColor(tokens.SELECTION))
        elif hovered:
            painter.fillRect(rect, QColor(tokens.CONTROL_HOVER))
        else:
            painter.fillRect(rect, QColor(tokens.PANEL))

        color = index.data(COLOR)
        if color:
            painter.fillRect(
                QRect(rect.left(), rect.top(), BAR_WIDTH, rect.height()),
                QColor(color),
            )

        right = rect.right() - RIGHT_PAD

        duration = index.data(DURATION)
        if duration:
            painter.setFont(self._timecode_font)
            metrics = QFontMetrics(self._timecode_font)
            width = metrics.horizontalAdvance("0:00")
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.drawText(
                QRect(right - width, rect.top(), width, rect.height()),
                Qt.AlignVCenter | Qt.AlignRight,
                str(duration),
            )
            right -= width + 10

        start = index.data(START)
        if start:
            painter.setFont(self._timecode_font)
            metrics = QFontMetrics(self._timecode_font)
            width = metrics.horizontalAdvance("00:00:00")
            painter.setPen(QColor(tokens.TEXT if selected else tokens.TEXT_MUTED))
            painter.drawText(
                QRect(right - width, rect.top(), width, rect.height()),
                Qt.AlignVCenter | Qt.AlignRight,
                str(start),
            )
            right -= width + 8

        cue = index.data(SOURCE_CUE)
        if cue:
            painter.setFont(self._cue_font)
            metrics = QFontMetrics(self._cue_font)
            width = metrics.horizontalAdvance(str(cue)) + 8
            pill = QRect(right - width, rect.center().y() - 8, width, 16)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(tokens.CONTROL))
            painter.drawRoundedRect(pill, tokens.RADIUS, tokens.RADIUS)
            painter.setPen(QColor(tokens.TEXT_FAINT))
            painter.drawText(pill, Qt.AlignCenter, str(cue))
            right -= width + 10

        title_left = rect.left() + BAR_WIDTH + BAR_GAP
        painter.setFont(self._title_font)
        painter.setPen(QColor(tokens.TEXT))
        metrics = QFontMetrics(self._title_font)
        available = max(0, right - title_left)
        painter.drawText(
            QRect(title_left, rect.top(), available, rect.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            metrics.elidedText(str(index.data(TITLE) or ""), Qt.ElideRight, available),
        )


class SidebarList(QTreeView):
    """Shared list behaviour: no header, no indentation, delegate-painted rows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setUniformRowHeights(False)
        self.setExpandsOnDoubleClick(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setMouseTracking(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setFrameShape(QTreeView.NoFrame)
        self.setItemDelegate(RowDelegate(self))
        self._model = QStandardItemModel(self)
        self.setModel(self._model)


class ClipList(SidebarList):
    """The dense Clip list, grouped by Category."""

    clip_selected = Signal(UUID)
    clip_activated = Signal(UUID)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.clicked.connect(self._clicked)
        self.doubleClicked.connect(self._double_clicked)
        self.selectionModel().currentChanged.connect(self._current_changed)
        self._show_source_cue = False
        # Reflecting a selection made elsewhere must not report back as a new
        # one, or selecting a Clip on the timeline would drag the playhead to
        # that Clip's start.
        self._reflecting = False

    def show_analysis(self, analysis: Analysis) -> None:
        self._model.clear()
        root = self._model.invisibleRootItem()
        self._show_source_cue = len(analysis.source_videos) > 1

        cues = {
            source.id: _source_cue(source.display_name)
            for source in analysis.source_videos
        }

        for category in analysis.categories:
            clips = [
                clip for clip in analysis.clips if clip.category_id == category.id
            ]
            if not clips:
                continue
            group = QStandardItem()
            group.setData(GROUP, KIND)
            group.setData(category.name, TITLE)
            group.setData(category.color, COLOR)
            group.setData(len(clips), COUNT)
            group.setSelectable(False)
            root.appendRow(group)

            for clip in sorted(clips, key=lambda one: one.start_ms):
                item = QStandardItem()
                item.setData(CLIP, KIND)
                item.setData(clip.name, TITLE)
                item.setData(category.color, COLOR)
                item.setData(fixture.timecode(clip.start_ms), START)
                item.setData(
                    fixture.duration_text(clip.end_ms - clip.start_ms), DURATION
                )
                item.setData(str(clip.id), ENTITY_ID)
                if self._show_source_cue:
                    item.setData(cues.get(clip.source_video_id, ""), SOURCE_CUE)
                item.setToolTip(clip.name)
                group.appendRow(item)

        self.expandAll()

    def select_clip(self, clip_id: UUID) -> None:
        index = self._index_of(clip_id)
        if not index.isValid() or index == self.currentIndex():
            return
        self._reflecting = True
        try:
            self.setCurrentIndex(index)
        finally:
            self._reflecting = False

    def _index_of(self, clip_id: UUID) -> QModelIndex:
        wanted = str(clip_id)
        for group_row in range(self._model.rowCount()):
            group = self._model.item(group_row)
            for row in range(group.rowCount()):
                child = group.child(row)
                if child.data(ENTITY_ID) == wanted:
                    return child.index()
        return QModelIndex()

    def _clicked(self, index: QModelIndex) -> None:
        if index.data(KIND) == GROUP:
            self.setExpanded(index, not self.isExpanded(index))

    def _current_changed(self, index: QModelIndex, _previous: QModelIndex) -> None:
        entity = index.data(ENTITY_ID)
        if entity and not self._reflecting:
            self.clip_selected.emit(UUID(entity))

    def _double_clicked(self, index: QModelIndex) -> None:
        entity = index.data(ENTITY_ID)
        if entity:
            self.clip_activated.emit(UUID(entity))


class VideoList(SidebarList):
    """The Source-video selector behind the Videos segment."""

    source_video_activated = Signal(UUID)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.selectionModel().currentChanged.connect(self._current_changed)

    def show_analysis(self, analysis: Analysis, active_id: UUID | None) -> None:
        self._model.clear()
        root = self._model.invisibleRootItem()
        for source in analysis.source_videos:
            clips = analysis.clips_of_source_video(source.id)
            item = QStandardItem()
            item.setData(SOURCE, KIND)
            item.setData(source.display_name, TITLE)
            item.setData(fixture.timecode(source.duration_ms or 0), START)
            item.setData(f"{len(clips)}", DURATION)
            item.setData(str(source.id), ENTITY_ID)
            item.setData(_source_cue(source.display_name), SOURCE_CUE)
            root.appendRow(item)
            if source.id == active_id:
                self.setCurrentIndex(item.index())

    def _current_changed(self, index: QModelIndex, _previous: QModelIndex) -> None:
        entity = index.data(ENTITY_ID)
        if entity:
            self.source_video_activated.emit(UUID(entity))


def _source_cue(display_name: str) -> str:
    """A two-character cue, so a Clip stays readable without the Videos tab."""
    digits = "".join(character for character in display_name if character.isdigit())
    initial = display_name[:1].upper() or "?"
    return f"{initial}{digits[-1:]}" if digits else initial
