"""THROWAWAY PROTOTYPE A -- the window, wired onto the existing seams.

This is a presentation layer only. It reads an ``analysis.Analysis`` and drives
a ``playback.Playback``; it contains no analytical logic of its own, which is
what makes the "how much Python does the presentation layer need" criterion
answerable by counting what is in this package.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from analysis.model import Analysis
from playback.player import Playback

from . import clip_list, controls, editor, fixture, stage, timeline, tokens, toolbar, transport

WORKSPACE = "workspace"
EDITING = "editing"
EMPTY = "empty"

_FAKE_TICK_MS = 33


class Workspace(QMainWindow):
    """The one window, in one of its three states."""

    def __init__(
        self,
        content: fixture.Fixture,
        player: Playback,
        *,
        poster: Path | None = None,
        drive_fake_playback: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Video Analyse")
        self.setMinimumSize(tokens.WINDOW_MIN_WIDTH, tokens.WINDOW_MIN_HEIGHT)

        self._content = content
        self._player = player
        self._screen = WORKSPACE
        self._selected_clip_id: UUID | None = content.selected_clip_id
        self._active_source_video_id = content.active_source_video_id

        self._build_menus()
        self._build_body(poster)
        self._connect()

        self._tick = QTimer(self)
        self._tick.setInterval(_FAKE_TICK_MS)
        self._tick.timeout.connect(self._advance_fake_playback)
        self._drive_fake_playback = drive_fake_playback

        self._load_active_source_video()
        self.show_screen(WORKSPACE)

    # ---------- construction ----------

    def _build_menus(self) -> None:
        """Native menu bar, native shortcuts. Behaviour stays platform-native."""
        file_menu = self.menuBar().addMenu("Datei")
        for label, shortcut in (
            ("Neue Analyse", QKeySequence.New),
            ("Analyse öffnen…", QKeySequence.Open),
            ("Analyse speichern", QKeySequence.Save),
        ):
            action = QAction(label, self)
            action.setShortcut(shortcut)
            file_menu.addAction(action)

        view_menu = self.menuBar().addMenu("Ansicht")
        for label, screen, shortcut in (
            ("Arbeitsbereich", WORKSPACE, "Ctrl+1"),
            ("Clip bearbeiten", EDITING, "Ctrl+2"),
            ("Leerer Zustand", EMPTY, "Ctrl+3"),
        ):
            action = QAction(label, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda _checked, name=screen: self.show_screen(name))
            view_menu.addAction(action)

        play = QAction("Wiedergabe", self)
        play.setShortcut(QKeySequence(Qt.Key_Space))
        play.triggered.connect(self._play_pause)
        self.addAction(play)

        mark = QAction("Clip markieren", self)
        mark.setShortcut(QKeySequence("R"))
        mark.triggered.connect(lambda: self.show_screen(EDITING))
        self.addAction(mark)

    def _build_body(self, poster: Path | None) -> None:
        self._toolbar = toolbar.Toolbar(self)
        self._toolbar.show_analysis(self._content.analysis.title, dirty=True)

        self._sidebar = self._build_sidebar()

        self._stage = stage.StageView(self)
        self._stage.set_poster(poster)
        self._empty_stage = stage.EmptyStage(self)

        self._stages = QStackedWidget(self)
        self._stages.addWidget(self._stage)
        self._stages.addWidget(self._empty_stage)

        self._timeline = timeline.Timeline(self)
        self._context = self._build_context_strip()
        self._transport = transport.Transport(self)

        centre = QWidget(self)
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.setSpacing(0)
        centre_layout.addWidget(self._stages, 1)
        centre_layout.addWidget(self._timeline)
        centre_layout.addWidget(self._context)
        centre_layout.addWidget(self._transport)

        self._editor = editor.ClipEditor(self)

        self._splitter = QSplitter(Qt.Horizontal, self)
        self._splitter.setHandleWidth(tokens.BORDER)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(centre)
        self._splitter.addWidget(self._editor)
        self._splitter.setStretchFactor(1, 1)

        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._toolbar)
        body_layout.addWidget(self._splitter, 1)
        self.setCentralWidget(body)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(tokens.SIDEBAR_MIN_WIDTH)
        sidebar.setMaximumWidth(tokens.SIDEBAR_MAX_WIDTH)

        self._segments = controls.SegmentedControl(["Clips", "Videos"], sidebar)
        self._clips = clip_list.ClipList(sidebar)
        self._videos = clip_list.VideoList(sidebar)

        self._panes = QStackedWidget(sidebar)
        self._panes.addWidget(self._clips)
        self._panes.addWidget(self._videos)
        self._segments.changed.connect(self._panes.setCurrentIndex)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(
            tokens.CONTROL_GAP, tokens.CONTROL_GAP, tokens.CONTROL_GAP, 0
        )
        layout.setSpacing(tokens.CONTROL_GAP)
        layout.addWidget(self._segments)
        layout.addWidget(self._panes, 1)
        return sidebar

    def _build_context_strip(self) -> QWidget:
        """The selected Clip's title and range, near the timeline."""
        strip = QWidget(self)
        strip.setFixedHeight(22)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(tokens.GUTTER, 0, tokens.GUTTER, 0)
        layout.setSpacing(tokens.CONTROL_GAP)

        self._context_title = QLabel(strip)
        self._context_range = controls.timecode_label("", muted=True)
        layout.addWidget(self._context_title)
        layout.addWidget(self._context_range)
        layout.addStretch(1)
        return strip

    # ---------- wiring ----------

    def _connect(self) -> None:
        self._player.position_changed.connect(self._position_changed)
        self._player.duration_changed.connect(self._duration_changed)
        self._player.playing_changed.connect(self._transport.set_playing)
        self._player.playing_changed.connect(self._playing_changed)

        self._timeline.scrubbed.connect(self._player.seek)
        self._timeline.clip_selected.connect(self._select_clip)
        self._timeline.clip_activated.connect(self._go_to_clip)

        self._clips.clip_selected.connect(self._go_to_clip)
        self._clips.clip_activated.connect(lambda _id: self.show_screen(EDITING))
        self._videos.source_video_activated.connect(self._activate_source_video)

        self._transport.play_pause_requested.connect(self._play_pause)
        self._transport.step_back_requested.connect(self._player.step_backward)
        self._transport.step_forward_requested.connect(self._player.step_forward)
        self._transport.jump_back_requested.connect(self._player.jump_backward)
        self._transport.jump_forward_requested.connect(self._player.jump_forward)
        self._transport.mute_toggled.connect(self._toggle_mute)
        self._transport.rate_changed.connect(self._player.set_playback_rate)
        self._transport.mark_clip_requested.connect(lambda: self.show_screen(EDITING))

        self._editor.boundary_scrubbed.connect(self._player.seek)
        self._editor.saved.connect(lambda: self.show_screen(WORKSPACE))
        self._editor.discarded.connect(lambda: self.show_screen(WORKSPACE))

        self._toolbar.sidebar_toggled.connect(self._toggle_sidebar)

    # ---------- state ----------

    def show_screen(self, screen: str) -> None:
        was = self._screen
        self._screen = screen
        self._editor.setVisible(screen == EDITING)
        self._sidebar.setVisible(screen != EDITING)
        self._stages.setCurrentIndex(1 if screen == EMPTY else 0)
        self._timeline.setVisible(screen != EMPTY)
        self._context.setVisible(screen != EMPTY)
        self._transport.setVisible(screen != EMPTY)
        self._transport.set_mark_visible(screen == WORKSPACE)

        # An Analysis with no Source videos is the normal workspace with empty
        # sidebar tabs, not a separate welcome screen.
        if screen == EMPTY:
            self._show_empty_sidebar()
        elif was == EMPTY:
            self._load_active_source_video()

        if screen == EDITING:
            self._player.pause()
            clip = self._content.analysis.clip(
                self._selected_clip_id or self._content.selected_clip_id
            )
            self._editor.show_clip(self._content.analysis, clip)
        self._apply_split()

    def _apply_split(self) -> None:
        width = max(self.width(), tokens.WINDOW_MIN_WIDTH)
        if self._screen == EDITING:
            self._splitter.setSizes([0, width - tokens.EDITOR_WIDTH, tokens.EDITOR_WIDTH])
        else:
            self._splitter.setSizes([tokens.SIDEBAR_WIDTH, width - tokens.SIDEBAR_WIDTH, 0])

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._apply_split()

    def _load_active_source_video(self) -> None:
        analysis = self._content.analysis
        source = analysis.source_video(self._active_source_video_id)

        self._clips.show_analysis(analysis)
        self._videos.show_analysis(analysis, self._active_source_video_id)
        self._timeline.show_source_video(
            analysis, source.id, source.duration_ms or 0
        )

        self._player.load(source.location)
        set_duration = getattr(self._player, "set_duration", None)
        if callable(set_duration):
            # FakePlayback stands in for the media announcing its duration.
            set_duration(source.duration_ms or 0)

        self._transport.set_duration(source.duration_ms or 0)
        self._player.seek(self._content.playhead_ms)
        if self._selected_clip_id is not None:
            self._select_clip(self._selected_clip_id)

    def _show_empty_sidebar(self) -> None:
        empty = Analysis(self._content.analysis.title)
        self._clips.show_analysis(empty)
        self._videos.show_analysis(empty, None)
        self._context_title.setText("")
        self._context_range.setText("")

    def _activate_source_video(self, source_video_id: UUID) -> None:
        if source_video_id == self._active_source_video_id:
            return
        self._active_source_video_id = source_video_id
        source = self._content.analysis.source_video(source_video_id)
        self._timeline.show_source_video(
            self._content.analysis, source.id, source.duration_ms or 0
        )
        self._player.load(source.location)
        set_duration = getattr(self._player, "set_duration", None)
        if callable(set_duration):
            set_duration(source.duration_ms or 0)
        self._transport.set_duration(source.duration_ms or 0)
        self._player.seek(0)

    def _select_clip(self, clip_id: UUID) -> None:
        """Select without moving the playhead: a click on a timeline range."""
        self._selected_clip_id = clip_id
        clip = self._content.analysis.clip(clip_id)
        self._timeline.set_selected_clip(clip_id)
        self._clips.select_clip(clip_id)
        self._context_title.setText(clip.name)
        self._context_range.setText(
            f"{fixture.timecode(clip.start_ms)} – {fixture.timecode(clip.end_ms)}"
        )

    def _go_to_clip(self, clip_id: UUID) -> None:
        """Selecting a Clip activates its Source video and seeks to its start."""
        clip = self._content.analysis.clip(clip_id)
        self._activate_source_video(clip.source_video_id)
        self._select_clip(clip_id)
        self._player.seek(clip.start_ms)

    def _position_changed(self, position_ms: int) -> None:
        self._timeline.set_position(position_ms)
        self._transport.set_position(position_ms)

    def _duration_changed(self, duration_ms: int) -> None:
        if duration_ms <= 0:
            return
        self._timeline.set_duration(duration_ms)
        self._transport.set_duration(duration_ms)

    def _play_pause(self) -> None:
        self._player.play_pause()

    def _playing_changed(self, playing: bool) -> None:
        if not self._drive_fake_playback:
            return
        self._tick.start() if playing else self._tick.stop()

    def _advance_fake_playback(self) -> None:
        """Move a fake player's position, so the playhead really animates."""
        step = int(_FAKE_TICK_MS * self._player.playback_rate())
        self._player.seek(self._player.position() + step)

    def _toggle_mute(self) -> None:
        self._player.toggle_muted()
        self._transport.set_muted(self._player.is_muted())

    def _toggle_sidebar(self) -> None:
        if self._screen == EDITING:
            return
        self._sidebar.setVisible(not self._sidebar.isVisible())
