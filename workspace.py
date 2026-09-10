"""The production workspace, composed in hand-written Python.

ADR 0005 retires the Designer main window: the validated direction is made of
layout *states* — a tab-switched sidebar, a dedicated Clip-editing state, and a
compact timeline — which a static widget tree expresses poorly. This module
composes the widget tree and carries the visual system recorded in
``docs/design/desktop-ux.md``. It holds no state and makes no decision: the
window mixed with it stays the controller, and every change to the Analysis
still goes through Analysis operations.

Two areas are deliberately left empty here, because they are composed by their
own tickets against this shell: the Clips and Videos sidebar panes (#15) and
the compact timeline (#27) that will live in the strip beneath the video.
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
from treewidget import TreeWidget
from videowidget import VideoWidget
from visual_system import RULE, WORKSPACE_STYLE_SHEET
import resources_rc  # noqa: F401  (registers the bundled icons)

PRODUCT_LABEL = "VIDEO ANALYSE"

CLIPS_TAB_LABEL = "Clips"
VIDEOS_TAB_LABEL = "Videos"

ADD_VIDEO_LABEL = "Video hinzufügen"
EMPTY_PLAYER_HINT = "Diese Analyse hat noch kein Quellvideo."

SIDEBAR_WIDTH = 320
VIDEO_MINIMUM_SIZE = QSize(360, 220)
CLIP_EDITOR_WIDTH = 380
TIMELINE_HEIGHT = 26

CLIP_COLUMN_LABELS = ("Clip", "Start", "Stop")

def _rule(orientation: Qt.Orientation = Qt.Horizontal) -> QFrame:
    """One thin separator; the workspace has no other pane divider."""
    rule = QFrame()
    rule.setFrameShape(
        QFrame.Shape.HLine if orientation == Qt.Horizontal else QFrame.Shape.VLine
    )
    rule.setFrameShadow(QFrame.Shadow.Plain)
    rule.setLineWidth(1)
    rule.setStyleSheet(f"color: {RULE}; background-color: {RULE};")
    if orientation == Qt.Horizontal:
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


class WorkspaceShell:
    """Composes the workspace onto the main window this is mixed into.

    Every widget it creates is named on the window, so the controller and its
    behavioral suite reach the workspace the same way they reached the Designer
    window it replaces.
    """

    def compose_workspace(self) -> None:
        self.setStyleSheet(WORKSPACE_STYLE_SHEET)
        self.setAcceptDrops(True)
        self.resize(1440, 900)

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
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.splitter.addWidget(self._compose_sidebar())
        self.splitter.addWidget(self._compose_video_area())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([SIDEBAR_WIDTH, 1000])
        return self.splitter

    def _compose_sidebar(self) -> QWidget:
        """The Clips and Videos tabs. Issue #15 fills the panes."""
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

        self.videosTab = QWidget()
        videos_layout = QVBoxLayout(self.videosTab)
        videos_layout.setContentsMargins(12, 12, 12, 12)
        videos_layout.setSpacing(8)
        videos_layout.addWidget(_label("QUELLVIDEOS", "section"))
        videos_layout.addStretch(1)

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
        layout.addWidget(_rule(Qt.Vertical))
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
        hint.setAlignment(Qt.AlignHCenter)
        hint_layout.addWidget(hint)
        hint_layout.addWidget(self.addVideoButton, 0, Qt.AlignHCenter)
        hint_layout.addStretch(1)

        self.playerStack = QStackedWidget()
        self.playerStack.addWidget(self.videoWidget)
        self.playerStack.addWidget(self.emptyPlayerHint)
        return self.playerStack

    def _compose_timeline_area(self) -> QWidget:
        """The compact strip directly beneath the video. Issue #27 fills it."""
        self.timelineArea = QFrame()
        self.timelineArea.setProperty("role", "pane")

        self.position_label = _label("00:00:00", "time")
        self.duration_label = _label("00:00:00", "time")
        self.timelineHost = QWidget()
        self.timelineHost.setProperty("role", "timeline")
        self.timelineHost.setFixedHeight(TIMELINE_HEIGHT)
        self.timelineHost.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        host_layout = QHBoxLayout(self.timelineHost)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        layout = QHBoxLayout(self.timelineArea)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)
        layout.addWidget(self.position_label)
        layout.addWidget(self.timelineHost, 1)
        layout.addWidget(self.duration_label)
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
        self.clipEditorArea.setProperty("role", "pane")
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
