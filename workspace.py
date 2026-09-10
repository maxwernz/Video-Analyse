"""The production workspace, composed in hand-written Python.

ADR 0005 retires the Designer main window: the validated direction is made of
layout *states* — a tab-switched sidebar, a dedicated Clip-editing state, and a
compact timeline — which a static widget tree expresses poorly. This module
composes the widget tree and carries the visual system recorded in
``docs/design/desktop-ux.md``. It holds no state and makes no decision: the
window mixed with it stays the controller, and every change to the Analysis
still goes through Analysis operations.

One area is deliberately left empty here, because it is composed by its own
ticket against this shell: the Clip-editing state beside the video (#26).
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application_workflow import UNTITLED_ANALYSIS_TITLE
from clip_handler import CreateClip, EditClip
from source_video_list import SourceVideoList
from timeline import Timeline
from treewidget import TreeWidget
from videowidget import VideoWidget
from visual_system import RULE, WORKSPACE_STYLE_SHEET
import resources_rc  # noqa: F401  (registers the bundled icons)

PRODUCT_LABEL = "VIDEO ANALYSE"

CLIPS_TAB_LABEL = "Clips"
VIDEOS_TAB_LABEL = "Videos"

ADD_VIDEO_LABEL = "Video hinzufügen"
EMPTY_PLAYER_HINT = "Diese Analyse hat noch kein Quellvideo."

#: The workspace opens at the smallest size the direction was validated at.
WORKSPACE_SIZE = (1280, 720)
SIDEBAR_WIDTH = 320
VIDEO_MINIMUM_SIZE = QSize(360, 220)
CLIP_EDITOR_WIDTH = 380
SELECTED_CLIP_HEIGHT = 14

SOURCE_VIDEO_COLUMN_LABEL = "Video"
#: The Clip list keeps its Source-video cue, so it reads without the Videos tab.
CLIP_COLUMN_LABELS = ("Clip", "Start", "Stop", SOURCE_VIDEO_COLUMN_LABEL)

def _rule(orientation: Qt.Orientation = Qt.Orientation.Horizontal) -> QFrame:
    """One thin separator; the workspace has no other pane divider."""
    rule = QFrame()
    rule.setFrameShape(
        QFrame.Shape.HLine if orientation == Qt.Orientation.Horizontal else QFrame.Shape.VLine
    )
    rule.setFrameShadow(QFrame.Shadow.Plain)
    rule.setLineWidth(1)
    rule.setStyleSheet(f"color: {RULE}; background-color: {RULE};")
    if orientation == Qt.Orientation.Horizontal:
        rule.setFixedHeight(1)
    else:
        rule.setFixedWidth(1)
    return rule


def _label(text: str, role: str = "") -> QLabel:
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    return label


def _transport_button(icon: QIcon, icon_size: QSize, checkable: bool = False) -> QPushButton:
    button = QPushButton()
    button.setProperty("role", "transport")
    button.setIcon(icon)
    button.setIconSize(icon_size)
    button.setCheckable(checkable)
    button.setFlat(True)
    return button


def _icon(off: str, on: str | None = None) -> QIcon:
    icon = QIcon()
    icon.addFile(f":/icons/{off}", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
    if on is not None:
        icon.addFile(f":/icons/{on}", QSize(), QIcon.Mode.Normal, QIcon.State.On)
    return icon


class WorkspaceShell(QMainWindow):
    """The window the production workspace is composed into.

    It is the hand-written replacement for the generated Designer window, and
    it plays the same part: the controller derives from it and reaches every
    widget by name, but no behavior lives here.
    """

    def compose_workspace(self) -> None:
        self.setStyleSheet(WORKSPACE_STYLE_SHEET)
        self.setAcceptDrops(True)
        self.resize(*WORKSPACE_SIZE)

        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)

        layout = QVBoxLayout(self.centralwidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._compose_header())
        layout.addWidget(self._compose_body(), 1)

    # --- Header ------------------------------------------------------------

    def _compose_header(self) -> QWidget:
        """The Analysis title, and how far an export has got."""
        self.headerBar = QFrame()
        self.headerBar.setProperty("role", "header")

        self.titleLabel = _label(UNTITLED_ANALYSIS_TITLE, "document")
        self.exportFinishedLabel = _label("Export erfolgreich", "muted")
        self.openExportButton = QPushButton("Öffnen")
        self.openExportButton.setProperty("role", "link")
        self.progressBar = QProgressBar()
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)

        layout = QHBoxLayout(self.headerBar)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        layout.addWidget(_label(PRODUCT_LABEL, "product"))
        layout.addWidget(self.titleLabel)
        layout.addStretch(1)
        layout.addWidget(self.exportFinishedLabel)
        layout.addWidget(self.openExportButton)
        layout.addWidget(self.progressBar)
        return self.headerBar

    # --- Body: sidebar, video area, Clip-editing state ---------------------

    def _compose_body(self) -> QWidget:
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.splitter.addWidget(self._compose_sidebar())
        self.splitter.addWidget(self._compose_video_area())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([SIDEBAR_WIDTH, 1000])
        return self.splitter

    def _compose_sidebar(self) -> QWidget:
        """The Clips and Videos tabs: the dense Clip list, and the video selector.

        The two panes are separate tabs rather than one list, so the Clip list
        stays dense; each Clip row carries its own Source-video cue, so the
        Clips tab stays readable while the Videos tab is not visible.
        """
        self.sidebar = QFrame()
        self.sidebar.setProperty("role", "pane")
        self.sidebar.setMinimumWidth(220)

        self.treeWidget = TreeWidget()
        self.treeWidget.setColumnCount(len(CLIP_COLUMN_LABELS))
        header_item = QTreeWidgetItem()
        for column, label in enumerate(CLIP_COLUMN_LABELS):
            header_item.setText(column, label)
        self.treeWidget.setHeaderItem(header_item)
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.treeWidget.setFrameShape(QFrame.Shape.NoFrame)
        self.treeWidget.setAcceptDrops(True)

        self.clipsTab = QWidget()
        clips_layout = QVBoxLayout(self.clipsTab)
        clips_layout.setContentsMargins(0, 0, 0, 0)
        clips_layout.addWidget(self.treeWidget)

        self.sourceVideoList = SourceVideoList()

        self.videosTab = QWidget()
        videos_layout = QVBoxLayout(self.videosTab)
        videos_layout.setContentsMargins(0, 0, 0, 0)
        videos_layout.addWidget(self.sourceVideoList)

        self.sidebarTabs = QTabWidget()
        self.sidebarTabs.setDocumentMode(True)
        self.sidebarTabs.addTab(self.clipsTab, CLIPS_TAB_LABEL)
        self.sidebarTabs.addTab(self.videosTab, VIDEOS_TAB_LABEL)

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebarTabs)
        return self.sidebar

    def _compose_video_area(self) -> QWidget:
        """The player, the timeline strip beneath it, and the transport."""
        video_column = QWidget()
        column_layout = QVBoxLayout(video_column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(0)
        column_layout.addWidget(self._compose_player(), 1)
        column_layout.addWidget(_rule())
        column_layout.addWidget(self._compose_timeline_area())
        column_layout.addWidget(_rule())
        column_layout.addWidget(self._compose_transport())

        area = QWidget()
        layout = QHBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(video_column, 1)
        layout.addWidget(self._compose_clip_editor())
        return area

    def _compose_player(self) -> QWidget:
        """One video surface, and the call to action while there is none.

        An Analysis without Source videos is the ordinary workspace with an
        empty player, so the call to action shares the player's place rather
        than becoming a screen of its own.
        """
        self.videoWidget = VideoWidget()
        self.videoWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoWidget.setMinimumSize(VIDEO_MINIMUM_SIZE)

        self.addVideoButton = QPushButton(ADD_VIDEO_LABEL)
        self.addVideoButton.setProperty("role", "primary")

        self.emptyPlayerHint = QFrame()
        self.emptyPlayerHint.setProperty("role", "stage")
        hint_layout = QVBoxLayout(self.emptyPlayerHint)
        hint_layout.setSpacing(12)
        hint_layout.addStretch(1)
        hint = _label(EMPTY_PLAYER_HINT, "muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint_layout.addWidget(hint)
        hint_layout.addWidget(self.addVideoButton, 0, Qt.AlignmentFlag.AlignHCenter)
        hint_layout.addStretch(1)

        self.playerStack = QStackedWidget()
        self.playerStack.addWidget(self.videoWidget)
        self.playerStack.addWidget(self.emptyPlayerHint)
        return self.playerStack

    def _compose_timeline_area(self) -> QWidget:
        """The compact strip directly beneath the video: the one seek surface.

        ADR 0006 gives the workspace a single timeline scoped to the Active
        Source video, and the selected Clip is named directly under it so the
        strip itself stays compact.
        """
        self.timelineArea = QFrame()
        self.timelineArea.setProperty("role", "pane")

        self.position_label = _label("00:00:00", "time")
        self.duration_label = _label("00:00:00", "time")
        self.timeline = Timeline()

        strip = QHBoxLayout()
        strip.setContentsMargins(0, 0, 0, 0)
        strip.setSpacing(10)
        strip.addWidget(self.position_label)
        strip.addWidget(self.timeline, 1)
        strip.addWidget(self.duration_label)

        self.selectedClipLabel = _label("", "muted")
        self.selectedClipLabel.setFixedHeight(SELECTED_CLIP_HEIGHT)

        layout = QVBoxLayout(self.timelineArea)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(2)
        layout.addLayout(strip)
        layout.addWidget(self.selectedClipLabel)
        return self.timelineArea

    def _compose_transport(self) -> QWidget:
        self.transportBar = QFrame()
        self.transportBar.setProperty("role", "pane")

        self.soundButton = _transport_button(
            _icon("speaker.wave.3.fill.on.png", "speaker.wave.3.fill.png"),
            QSize(22, 22),
            checkable=True,
        )
        self.backwardButton = _transport_button(
            _icon("backward.fill.png"), QSize(26, 14)
        )
        self.playPauseButton = _transport_button(
            _icon("custom.play.fill.png", "pause.fill.png"),
            QSize(20, 20),
            checkable=True,
        )
        self.forwardButton = _transport_button(
            _icon("forward.fill.png"), QSize(26, 14)
        )
        self.clipButton = _transport_button(
            _icon("record.circle.png", "record.circle.action.png"),
            QSize(22, 22),
            checkable=True,
        )
        self.speedBox = QComboBox()
        self.speedBox.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        layout = QHBoxLayout(self.transportBar)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(6)
        layout.addWidget(self.soundButton)
        layout.addStretch(1)
        layout.addWidget(self.backwardButton)
        layout.addWidget(self.playPauseButton)
        layout.addWidget(self.forwardButton)
        layout.addWidget(self.speedBox)
        layout.addStretch(1)
        layout.addWidget(self.clipButton)
        return self.transportBar

    def _compose_clip_editor(self) -> QWidget:
        """Room beside the video for the Clip-editing state. Issue #26 fills it.

        The forms stay the Designer ones: a static form is what Designer is
        good at, so ``clip_handler.ui`` and its ``ClipDraft`` seam are reused
        unchanged. While neither is shown the area takes no space at all, so
        normal review keeps the full video width.
        """
        self.clipEditorArea = QFrame()
        self.clipEditorArea.setProperty("role", "editor")
        self.clipEditorArea.setMaximumWidth(CLIP_EDITOR_WIDTH)

        self.clipHandler = CreateClip()
        self.editHandler = EditClip()
        self.clipHandler.setVisible(False)
        self.editHandler.setVisible(False)

        layout = QVBoxLayout(self.clipEditorArea)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.clipHandler)
        layout.addWidget(self.editHandler)
        layout.addStretch(1)
        return self.clipEditorArea
