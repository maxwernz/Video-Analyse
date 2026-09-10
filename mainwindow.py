import sys
import os
from dataclasses import dataclass
from uuid import UUID
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)
from PySide6 import QtCore
from PySide6.QtCore import QUrl, QEvent, Qt, QSignalBlocker, Signal, Property, QTranslator, QTimer, QStandardPaths
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QDesktopServices
from analysis import (
    Analysis,
    AnalysisDocument,
    AnalysisError,
    SourceVideo,
    UnsavedChangesChoice,
)
from application_workflow import (
    ANALYSIS_FILE_FILTER,
    SOURCE_VIDEO_FILE_FILTER,
    UNTITLED_ANALYSIS_TITLE,
    ApplicationWorkflow,
)
from playback import Playback
from timeline import TimelineRange
from visual_system import MESSAGE_BOX_STYLE_SHEET
from workspace import WorkspaceShell
from treewidget_item import ClipItem
from video_creator import VideoCreator, ProgressLogger
from util import milliseconds_to_hhmmss

basedir = os.path.dirname(__file__)

PLAYBACK_RATES = (0.25, 0.5, 1.0, 2.0)
"""The rates the speed selector offers, in the order it lists them."""

DEFAULT_PLAYBACK_RATE = 1.0

SELECTED_CLIP_FORMAT = "{name}  ·  {start} – {end}"
"""How the Clip selected on the timeline is named beneath it."""


@dataclass(frozen=True)
class PendingClip:
    """A Clip boundary marked on one Source video, before it is a Clip.

    It is not part of the Analysis, and it carries the identity of the Source
    video its start was marked on, so the Clip it becomes belongs there and
    nowhere else.
    """

    source_video_id: UUID
    start_ms: int


class MainWindow(WorkspaceShell):
    """Drives one Analysis document; the Analysis owns all durable state."""

    file_changed = Signal(str)
    file_changes_made = Signal(bool)

    def __init__(self, parent=None, playback: Playback | None = None):
        super().__init__()
        # self.set_language('de')
        self.compose_workspace()

        if playback is not None:
            self.videoWidget.set_player(playback)
        self.player = self.videoWidget.player
        self.setup_playback_rates()

        self.export_timer = QTimer()

        self.setup_document_commands()
        self.setup_connections()
        self.setup_shortcuts()

        self.progressBar.setVisible(False)
        self.openExportButton.setVisible(False)
        self.exportFinishedLabel.setVisible(False)

        self.titleLabel.installEventFilter(self)

        self.pending_clip: PendingClip | None = None
        self._active_source_video_id = None
        self._selected_clip_id = None
        self._position_ms = 0
        self._duration_ms = 0
        self._current_file = None
        self.file_changed.emit(None)
        self._is_saved = True
        self.workflow = ApplicationWorkflow(
            self,
            on_analysis_replaced=self.analysis_replaced,
            on_document_changed=self.render_analysis,
            on_source_video_added=self.source_video_added,
        )
        self.render_analysis()

    def set_language(self, lang_code):
        translator = QTranslator()
        translator.load('qtbase_' + lang_code, ':/translations')
        QApplication.instance().installTranslator(translator)

    def setup_connections(self):
        self.playPauseButton.clicked.connect(self.play_pause)
        self.player.playing_changed.connect(self.show_playing_state)
        self.soundButton.clicked.connect(self.player.toggle_muted)
        self.forwardButton.clicked.connect(self.player.jump_forward)
        self.backwardButton.clicked.connect(self.player.jump_backward)
        self.clipButton.toggled.connect(lambda recording: self.clip_started() if recording else self.clip_stopped())
        self.speedBox.currentIndexChanged.connect(self.apply_playback_rate)
        self.player.position_changed.connect(self.position_changed)
        self.player.duration_changed.connect(self.duration_changed)

        self.timeline.scrubbed.connect(self.player.seek)
        self.timeline.clip_selected.connect(self.select_clip)
        self.timeline.clip_activated.connect(self.navigate_to_clip)

        self.addVideoButton.clicked.connect(self.open_video)

        self.sourceVideoList.source_video_activated.connect(self.activate_source_video)

        self.treeWidget.clip_activated.connect(self.navigate_to_clip)
        self.treeWidget.export_clips.connect(self.export)
        self.treeWidget.clip_edit_requested.connect(self.edit_clip)
        self.treeWidget.clip_remove_requested.connect(self.remove_clip)
        self.treeWidget.category_edit_requested.connect(self.rename_category)
        self.treeWidget.category_remove_requested.connect(self.remove_category)

        self.clipHandler.clip_submitted.connect(self.create_clip)
        self.clipHandler.cancelButton.clicked.connect(self.discard_pending_clip)
        self.editHandler.clip_submitted.connect(self.apply_clip_edit)
        self.editHandler.cancelButton.clicked.connect(self.disable_edit_handler)

        self.export_timer.timeout.connect(lambda: self.exportFinishedLabel.setVisible(False))
        self.export_timer.timeout.connect(lambda: self.openExportButton.setVisible(False))
        self.export_timer.timeout.connect(self.openExportButton.clicked.disconnect)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.player.step_forward)
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.player.step_backward)
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(self.change_speed_up)
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(self.change_speed_down)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self).activated.connect(self.rename_analysis)

    def setup_document_commands(self):
        """Name, shortcut, and order every command of the File menu.

        The commands keep the attribute names the Designer window gave them,
        so that the behavioral suite still reaches them by the same handles.
        """
        self.actionAnalyse_entfernen = QAction("Neue Analyse", self)
        self.actionAnalyse_entfernen.setShortcut(QKeySequence.StandardKey.New)
        self.actionAnalyse_laden = QAction("Analyse öffnen …", self)
        self.actionAnalyse_laden.setShortcut(QKeySequence.StandardKey.Open)
        self.actionAnalyse_speichern = QAction("Analyse speichern", self)
        self.actionAnalyse_speichern.setShortcut(QKeySequence.StandardKey.Save)
        self.actionAnalyse_speichern_unter = QAction("Analyse speichern unter …", self)
        self.actionAnalyse_speichern_unter.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.actionAnalyse_schliessen = QAction("Schließen", self)
        self.actionAnalyse_schliessen.setShortcut(QKeySequence.StandardKey.Close)
        self.actionLoad_Video = QAction("Video hinzufügen …", self)
        self.actionLoad_Video.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.actionClips_Exportieren = QAction("Clips exportieren", self)
        self.actionClips_Exportieren.setShortcut(QKeySequence("Ctrl+E"))
        self.actionVideo_Exportieren = QAction("Video exportieren", self)
        self.actionVideo_Exportieren.setShortcut(QKeySequence("Ctrl+Shift+E"))

        self.actionAnalyse_entfernen.triggered.connect(self.new_analysis)
        self.actionAnalyse_laden.triggered.connect(self.open_analysis)
        self.actionAnalyse_speichern.triggered.connect(self.save_analysis)
        self.actionAnalyse_speichern_unter.triggered.connect(self.save_analysis_as)
        self.actionLoad_Video.triggered.connect(self.open_video)
        self.actionAnalyse_schliessen.triggered.connect(self.close)
        self.actionClips_Exportieren.triggered.connect(self.export)
        self.actionVideo_Exportieren.triggered.connect(
            lambda: self.export(include_all_clips=True)
        )

        self.menubar = self.menuBar()
        self.menuFile = self.menubar.addMenu("Datei")
        self.menuFile.addAction(self.actionAnalyse_entfernen)
        self.menuFile.addAction(self.actionAnalyse_laden)
        self.menuFile.addAction(self.actionAnalyse_speichern)
        self.menuFile.addAction(self.actionAnalyse_speichern_unter)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionLoad_Video)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionClips_Exportieren)
        self.menuFile.addAction(self.actionVideo_Exportieren)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionAnalyse_schliessen)

    @property
    def document(self) -> AnalysisDocument:
        return self.workflow.document

    @document.setter
    def document(self, document: AnalysisDocument) -> None:
        self.workflow.adopt_document(document)

    @property
    def analysis(self) -> Analysis:
        return self.workflow.analysis

    def closeEvent(self, event):
        if self.may_replace_analysis():
            event.accept()
        else:
            event.ignore()

    def may_replace_analysis(self) -> bool:
        """Ask about unsaved changes before the current Analysis is let go."""
        return self.workflow.may_replace_analysis()

    def analysis_replaced(self):
        """A different Analysis is open now; drop everything transient."""
        self._active_source_video_id = None
        self._selected_clip_id = None
        self._position_ms = 0
        self._duration_ms = 0
        self.discard_pending_clip()
        self.disable_edit_handler()
        self.player.unload()
        self.activate_first_source_video()

    def activate_first_source_video(self):
        source_video = self.active_source_video()
        if source_video is None:
            return
        if os.path.exists(source_video.location):
            self.load_media(source_video)
        else:
            QMessageBox.warning(
                self,
                "Source video not found",
                "The Analysis was opened, but its Source video must be relinked.",
            )

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Ungespeicherte Änderungen")
        message_box.setText("Es gibt ungespeicherte Änderungen. Möchten sie speichern?")
        message_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        message_box.setStyleSheet(MESSAGE_BOX_STYLE_SHEET)
        reply = message_box.exec()

        if reply == QMessageBox.Save:
            return UnsavedChangesChoice.SAVE
        if reply == QMessageBox.Discard:
            return UnsavedChangesChoice.DISCARD
        return UnsavedChangesChoice.CANCEL

    @Property(str, notify=file_changed)
    def current_file(self):
        return self._current_file

    @current_file.setter
    def current_file(self, value):
        if self._current_file != value:
            self._current_file = value
            self.file_changed.emit(value)

    @Property(bool, notify=file_changes_made)
    def is_saved(self):
        return self._is_saved

    @is_saved.setter
    def is_saved(self, value):
        if self._is_saved != value:
            self._is_saved = value
            self.file_changes_made.emit(value)

    def render_analysis(self):
        """Render the Analysis; it stays the single source of truth."""
        analysis = self.analysis
        self.titleLabel.setText(analysis.title or UNTITLED_ANALYSIS_TITLE)
        self.treeWidget.render_analysis(analysis)
        self.render_source_videos()
        self.render_player_state()
        self.render_timeline()
        self.refresh_document_state()

    def render_source_videos(self):
        """Show every Source video of the Analysis, the active one chosen.

        The Active Source video is resolved rather than read, because with
        nothing activated yet it is the first Source video of the Analysis,
        and that is the one the player shows.
        """
        active = self.active_source_video()
        self.sourceVideoList.render_analysis(
            self.analysis, None if active is None else active.id
        )

    def render_player_state(self):
        """Show the call to action while the Analysis has no Source video.

        This is the ordinary workspace either way: only the player's own place
        changes, so the first video arriving is a repaint and not a different
        screen with different rules.
        """
        has_source_videos = bool(self.analysis.source_videos)
        self.playerStack.setCurrentWidget(
            self.videoWidget if has_source_videos else self.emptyPlayerHint
        )

    def render_timeline(self):
        """Scope the timeline to the Active Source video, and to it alone."""
        source_video = self.active_source_video()
        ranges = () if source_video is None else self.timeline_ranges(source_video)
        self.timeline.show_ranges(ranges)
        self.timeline.set_duration(self._duration_ms)
        self.timeline.set_position(self._position_ms)
        self.select_clip(self.selection_within(ranges))

    def selection_within(self, ranges):
        """Keep the selected Clip only while the timeline still shows it."""
        return next(
            (
                shown.clip_id
                for shown in ranges
                if shown.clip_id == self._selected_clip_id
            ),
            None,
        )

    def timeline_ranges(self, source_video: SourceVideo) -> tuple[TimelineRange, ...]:
        return tuple(
            TimelineRange(
                clip.id,
                clip.start_ms,
                clip.end_ms,
                self.category_color(clip.category_id),
            )
            for clip in self.analysis.clips_of_source_video(source_video.id)
        )

    def category_color(self, category_id):
        if category_id is None:
            return None
        try:
            return self.analysis.category(category_id).color
        except AnalysisError:
            return None

    def render_selected_clip(self):
        """Name the selected Clip and its interval directly under the strip."""
        clip = self.selected_clip()
        self.selectedClipLabel.setText(
            ""
            if clip is None
            else SELECTED_CLIP_FORMAT.format(
                name=clip.name,
                start=milliseconds_to_hhmmss(clip.start_ms),
                end=milliseconds_to_hhmmss(clip.end_ms),
            )
        )

    def refresh_document_state(self):
        self.current_file = (
            None if self.document.path is None else str(self.document.path)
        )
        self.is_saved = not self.document.dirty
        self.setWindowTitle(self.workflow.window_title)

    def eventFilter(self, watched, event):
        if watched is self.titleLabel and event.type() == QEvent.MouseButtonDblClick:
            self.rename_analysis()
            return True
        return super().eventFilter(watched, event)

    def rename_analysis(self):
        title, accepted = QInputDialog.getText(
            self,
            "Analyse umbenennen",
            "Titel:",
            text=self.analysis.title,
        )
        if not accepted:
            return
        self.apply_analysis_change(
            lambda: self.analysis.set_title(title.strip()),
            "Analysis could not be renamed",
        )

    def apply_analysis_change(self, change, failure_title) -> bool:
        """Run one Analysis operation, reporting the invariant it violated."""
        try:
            change()
        except AnalysisError as error:
            QMessageBox.critical(self, failure_title, str(error))
            return False
        self.render_analysis()
        return True

    def setup_playback_rates(self):
        """Offer each speed as a number, so nothing parses the label text."""
        with QSignalBlocker(self.speedBox):
            self.speedBox.clear()
            for rate in PLAYBACK_RATES:
                self.speedBox.addItem(f"{rate:g}x", rate)
            self.speedBox.setCurrentIndex(PLAYBACK_RATES.index(DEFAULT_PLAYBACK_RATE))
        self.apply_playback_rate()

    def apply_playback_rate(self):
        self.player.set_playback_rate(float(self.speedBox.currentData()))

    def play_pause(self):
        """Toggle playback, then report what the player actually does."""
        self.player.play_pause()
        self.show_playing_state(self.player.is_playing())

    def show_playing_state(self, playing: bool):
        """Keep the play control honest about what the player is doing."""
        with QSignalBlocker(self.playPauseButton):
            self.playPauseButton.setChecked(playing)

    def open_video(self):
        """Add a Source video chosen from a dialog to the current Analysis."""
        self.workflow.add_source_video()

    def load_video(self, file_name):
        """Add a Source video by path; it never replaces the current Analysis."""
        if not file_name:
            return
        self.workflow.add_source_video_file(file_name)

    def drop_file(self, path) -> bool:
        """Add a dropped video, or open a dropped Analysis file."""
        return self.workflow.open_dropped_file(path)

    def source_video_added(self, source_video: SourceVideo):
        """Show a newly added Source video only when nothing is playing yet.

        Adding footage must never interrupt the video under review, so the
        player stays where it is; the Videos sidebar tab is where a person
        chooses which Source video to switch to.
        """
        if self.active_source_video() is source_video:
            self.load_media(source_video)

    def load_media(self, source_video: SourceVideo):
        """Show a Source video, whose length only the player can report.

        Until it does, the workspace draws no length at all: keeping the one
        the previous Source video had would put the timeline's Clip ranges on
        the wrong time scale.
        """
        self.duration_changed(0)
        self.position_changed(0)
        self.player.load(source_video.location)

    def active_source_video(self) -> SourceVideo | None:
        """The Source video the one player shows; transient, never stored."""
        source_videos = self.analysis.source_videos
        active = next(
            (
                source_video
                for source_video in source_videos
                if source_video.id == self._active_source_video_id
            ),
            None,
        )
        if active is not None:
            return active
        return source_videos[0] if source_videos else None

    def activate_source_video(self, source_video_id):
        """Load a Source video into the one player and rescope the timeline.

        The Source video already under review is never reloaded: that would
        drop the frame being watched and the duration the timeline draws on.
        """
        active = self.active_source_video()
        if active is not None and active.id == source_video_id:
            self._active_source_video_id = source_video_id
            return
        try:
            source_video = self.analysis.source_video(source_video_id)
        except AnalysisError:
            self.render_source_videos()
            return
        self.discard_pending_clip()
        self._active_source_video_id = source_video_id
        self.load_media(source_video)
        self.render_player_state()
        self.render_source_videos()
        self.render_timeline()

    def navigate_to_clip(self, clip_id):
        """Go to a Clip: activate its Source video and seek to its start.

        This is the one way into a Clip from anywhere in the workspace, so the
        Clips sidebar tab (#15) and a double-click on the timeline arrive the
        same way and the timeline follows either.
        """
        try:
            clip = self.analysis.clip(clip_id)
        except AnalysisError:
            return
        self.activate_source_video(clip.source_video_id)
        self.select_clip(clip_id)
        self.player.seek(clip.start_ms)

    def select_clip(self, clip_id):
        """Select a Clip without moving the playhead; selection is transient."""
        self._selected_clip_id = clip_id
        self.timeline.set_selected_clip(clip_id)
        self.render_selected_clip()

    def selected_clip(self):
        if self._selected_clip_id is None:
            return None
        try:
            return self.analysis.clip(self._selected_clip_id)
        except AnalysisError:
            return None

    def save_analysis(self) -> bool:
        return self.workflow.save()

    def save_analysis_as(self) -> bool:
        return self.workflow.save_as()

    def open_analysis(self) -> bool:
        return self.workflow.open_analysis()

    def load_analysis(self, file_name) -> bool:
        if not file_name:
            return False
        return self.workflow.open_analysis_file(file_name)

    # --- What the workflow asks of the person ------------------------------

    def choose_source_video(self) -> str | None:
        return QFileDialog.getOpenFileName(
            self,
            "Video hinzufügen",
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MoviesLocation
            ),
            SOURCE_VIDEO_FILE_FILTER,
        )[0] or None

    def choose_analysis_to_open(self) -> str | None:
        return QFileDialog.getOpenFileName(
            self,
            "Analyse öffnen",
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            ),
            ANALYSIS_FILE_FILTER,
        )[0] or None

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        documents_directory = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        return QFileDialog.getSaveFileName(
            self,
            "Analyse speichern",
            os.path.join(documents_directory, suggested_name),
            ANALYSIS_FILE_FILTER,
        )[0] or None

    def report_failure(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def change_speed_up(self):
        current_index = self.speedBox.currentIndex()
        if current_index == self.speedBox.count() - 1:
            return

        self.speedBox.setCurrentIndex(current_index + 1)

    def change_speed_down(self):
        current_index = self.speedBox.currentIndex()
        if current_index == 0:
            return
        self.speedBox.setCurrentIndex(current_index - 1)

    def clip_started(self):
        """Begin a Pending Clip, bound to the Active Source video."""
        source_video = self.active_source_video()
        if source_video is None:
            self.discard_pending_clip()
            QMessageBox.information(
                self,
                "Kein Video",
                "Ein Clip braucht ein geladenes Video.",
            )
            return
        self.pending_clip = PendingClip(source_video.id, self.player.position())

    def clip_stopped(self):
        """Complete the second boundary of the Pending Clip, and describe it."""
        self.pause_for_clip_editing()
        if self.pending_clip is None:
            return

        self.disable_edit_handler()
        self.clipHandler.new_clip(
            self.pending_clip.start_ms,
            self.player.position(),
            self.category_names(),
        )
        self.clipHandler.setVisible(True)
        self.render_clip_editing_state()

    def discard_pending_clip(self):
        """Drop the Pending Clip; it was never part of the Analysis.

        Switching the player to another Source video abandons the mark, so
        the workspace can never assemble a Clip out of two Source videos. The
        record control follows, which is where the abandoning is seen.
        """
        self.pending_clip = None
        with QSignalBlocker(self.clipButton):
            self.clipButton.setChecked(False)
        self.disable_clip_handler()

    def category_names(self) -> list[str]:
        return [category.name for category in self.analysis.categories]

    def category_id_for(self, category_name):
        """Resolve a Category name to its identity, creating it when it is new."""
        if category_name is None:
            return None
        category = self.analysis.category_named(category_name)
        if category is not None:
            return category.id
        return self.analysis.add_category(category_name).id

    def create_clip(self, draft):
        """Add the described Clip to the Source video its mark began on."""
        if self.pending_clip is None:
            return
        source_video_id = self.pending_clip.source_video_id

        def add_clip():
            with self.analysis.transaction():
                self.analysis.add_clip(
                    source_video_id,
                    draft.name,
                    draft.start_ms,
                    draft.end_ms,
                    notes=draft.notes,
                    category_id=self.category_id_for(draft.category_name),
                )

        if self.apply_analysis_change(add_clip, "Clip could not be created"):
            self.discard_pending_clip()

    def pause_for_clip_editing(self):
        """The Clip-editing state keeps a paused frame; the transport follows."""
        self.player.pause()
        self.show_playing_state(self.player.is_playing())

    def edit_clip(self, clip_id):
        """Open the one Clip editor on a Clip the Analysis already holds."""
        try:
            clip = self.analysis.clip(clip_id)
        except AnalysisError:
            return
        self.pause_for_clip_editing()
        self.discard_pending_clip()
        category_name = (
            None
            if clip.category_id is None
            else self.analysis.category(clip.category_id).name
        )

        self.editHandler.new_clip(
            ClipItem.from_clip(clip, category_name),
            self.category_names(),
        )
        self.editHandler.setVisible(True)
        self.render_clip_editing_state()

    def apply_clip_edit(self, draft):
        if draft.clip_id is None:
            return

        def update_clip():
            with self.analysis.transaction():
                self.analysis.update_clip(
                    draft.clip_id,
                    name=draft.name,
                    start_ms=draft.start_ms,
                    end_ms=draft.end_ms,
                    notes=draft.notes,
                    category_id=self.category_id_for(draft.category_name),
                )

        if self.apply_analysis_change(update_clip, "Clip could not be changed"):
            self.disable_edit_handler()

    def remove_clip(self, clip_id):
        self.apply_analysis_change(
            lambda: self.analysis.remove_clip(clip_id),
            "Clip could not be removed",
        )

    def rename_category(self, category_id):
        try:
            category = self.analysis.category(category_id)
        except AnalysisError:
            return
        name, accepted = QInputDialog.getText(
            self,
            "Kategorie umbenennen",
            "Name:",
            text=category.name,
        )
        if not accepted:
            return
        self.apply_analysis_change(
            lambda: self.analysis.update_category(category_id, name=name),
            "Category could not be renamed",
        )

    def remove_category(self, category_id):
        """Remove a Category; its Clips stay in the Analysis as uncategorized."""
        self.apply_analysis_change(
            lambda: self.analysis.remove_category(category_id),
            "Category could not be removed",
        )

    def disable_clip_handler(self):
        self.clipHandler.setVisible(False)
        self.render_clip_editing_state()

    def disable_edit_handler(self):
        self.editHandler.setVisible(False)
        self.render_clip_editing_state()

    def render_clip_editing_state(self):
        """Let the editing area take room only while one of its forms is shown.

        Hiding a form does not by itself make the area beside the video give
        the width back that it grew to, so its layout is asked again. Leaving
        the Clip-editing state is what returns the video to its full size.
        """
        self.clipEditorArea.layout().invalidate()
        self.clipEditorArea.updateGeometry()

    def export(self, include_all_clips=False):
        source_video = self.active_source_video()
        if source_video is None:
            QMessageBox.information(self, "Info", "No video loaded")
            return

        if include_all_clips:
            clips = self.treeWidget.all_clip_items()
        else:
            clips = self.treeWidget.selected_clip_items()
        if not clips:
            QMessageBox.information(self, "Info", "No Clips selected")
            return

        export_directory = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.MoviesLocation
        )
        file_name = QFileDialog.getSaveFileName(
            self,
            "Save file",
            os.path.join(export_directory, "Clips.mp4"),
            "Video Datei (*.mp4)",
        )[0]
        if not file_name:
            return

        logger = ProgressLogger()
        video_creator = VideoCreator(
            clips,
            source_video.location,
            file_name,
            include_analysis_title=include_all_clips,
            logger=logger,
        )
        self.progressBar.setVisible(True)
        logger.progress_changed.connect(self.progressBar.setValue)
        logger.export_finished.connect(lambda: self.export_finished(file_name))

        try:
            video_creator.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def export_finished(self, file_name):
        self.progressBar.setVisible(False)
        self.exportFinishedLabel.setVisible(True)
        self.openExportButton.setVisible(True)
        self.openExportButton.clicked.connect(lambda: self.open_file_explorer(file_name))
        self.export_timer.start(10000)

    def new_analysis(self) -> bool:
        """The New Analysis command: let the current Analysis go and start empty."""
        return self.workflow.new_analysis()

    def open_file_explorer(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

            url = str(event.mimeData().urls()[0].toLocalFile())
            self.drop_file(url)
        else:
            event.ignore()

    def position_changed(self, position):
        self._position_ms = position
        self.set_position_label(position)
        self.timeline.set_position(position)

    def duration_changed(self, duration):
        self._duration_ms = duration
        self.set_duration_label(duration)
        self.timeline.set_duration(duration)

    def set_position_label(self, position):
        self.position_label.setText(f"{milliseconds_to_hhmmss(position)}")

    def set_duration_label(self, duration):
        self.duration_label.setText(f"{milliseconds_to_hhmmss(duration)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
