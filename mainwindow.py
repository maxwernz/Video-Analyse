import sys
import os
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
from Ui_main_window import Ui_MainWindow
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
    ApplicationWorkflow,
)
from playback import Playback
from treewidget_item import ClipItem, ClipTreeItem
from video_creator import VideoCreator, ProgressLogger
from util import milliseconds_to_hhmmss

basedir = os.path.dirname(__file__)

MESSAGE_BOX_STYLE_SHEET = """
    QMessageBox {
        background-color: rgb(31, 31, 31); /* Dark background for the message box */
        border: 2px solid rgb(65, 65, 65); /* Border around the message box */
        border-radius: 10px; /* Rounded corners */
        color: white; /* Text color */
    }

    /* Style the QLabel (main text in the box) */
    QMessageBox QLabel {
        color: white; /* Main text color */
        font: 14px "Segoe UI", sans-serif;
    }

    /* Style for the QPushButton within the QMessageBox */
    QMessageBox QPushButton {
        background-color: rgb(45, 45, 45); /* Button background */
        color: white; /* Button text color */
        border: 2px solid rgb(65, 65, 65); /* Button border */
        border-radius: 5px;
        padding: 5px 10px;
        font: 14px "Segoe UI", sans-serif;
    }

    QMessageBox QPushButton:hover {
        background-color: rgb(66, 65, 64); /* Background color on hover */
    }

    QMessageBox QPushButton:pressed {
        background-color: rgb(80, 80, 80); /* Darker color when pressed */
    }
"""

UNTITLED_ANALYSIS_LABEL = "No Video"

PLAYBACK_RATES = (0.25, 0.5, 1.0, 2.0)
"""The rates offered by the speed selector, in the order it lists them."""


class MainWindow(QMainWindow, Ui_MainWindow):
    """Drives one Analysis document; the Analysis owns all durable state."""

    file_changed = Signal(str)
    file_changes_made = Signal(bool)

    def __init__(self, parent=None, playback: Playback | None = None):
        super().__init__()
        # self.set_language('de')
        self.setupUi(self)

        if playback is not None:
            self.videoWidget.set_playback(playback)
        self.player = self.videoWidget.playback
        self.setup_playback_rates()

        self.actionClips_Exportieren.triggered.connect(self.export)
        self.actionVideo_Exportieren.triggered.connect(
            lambda: self.export(include_all_clips=True)
        )
        self.position_slider.sliderMoved.connect(self.player.seek)

        self.export_timer = QTimer()

        self.setup_document_commands()
        self.setup_connections()
        self.setup_shortcuts()

        self.progressBar.setVisible(False)
        self.openExportButton.setVisible(False)
        self.exportFinishedLabel.setVisible(False)
        self.clipHandler.setVisible(False)
        self.editHandler.setVisible(False)

        self.setAcceptDrops(True)
        self.titleLabel.installEventFilter(self)

        self.pending_clip_start = None
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
        self.playPauseButton.clicked.connect(self.player.play_pause)
        self.player.playing_changed.connect(self.show_playing_state)
        self.soundButton.clicked.connect(self.player.toggle_muted)
        self.forwardButton.clicked.connect(self.player.jump_forward)
        self.backwardButton.clicked.connect(self.player.jump_backward)
        self.clipButton.toggled.connect(lambda recording: self.clip_started() if recording else self.clip_stopped())
        self.speedBox.currentIndexChanged.connect(self.apply_playback_rate)
        self.player.position_changed.connect(self.position_changed)
        self.player.duration_changed.connect(self.duration_changed)

        self.treeWidget.itemClicked.connect(self.jump_to_clip)
        self.treeWidget.export_clips.connect(self.export)
        self.treeWidget.clip_edit_requested.connect(self.edit_clip)
        self.treeWidget.clip_remove_requested.connect(self.remove_clip)
        self.treeWidget.category_edit_requested.connect(self.rename_category)
        self.treeWidget.category_remove_requested.connect(self.remove_category)

        self.clipHandler.clip_submitted.connect(self.create_clip)
        self.clipHandler.cancelButton.clicked.connect(self.disable_clip_handler)
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
        """Give the Analysis document commands menu entries and shortcuts.

        The Designer file still describes the original single-video menu, so
        the commands are named, shortcut, and ordered here. Issue #25 retires
        that file and this stays the definition.
        """
        self.actionAnalyse_entfernen.setText("Neue Analyse")
        self.actionAnalyse_entfernen.setShortcut(QKeySequence.StandardKey.New)
        self.actionAnalyse_laden.setText("Analyse öffnen …")
        self.actionAnalyse_laden.setShortcut(QKeySequence.StandardKey.Open)
        self.actionAnalyse_speichern.setText("Analyse speichern")
        self.actionAnalyse_speichern.setShortcut(QKeySequence.StandardKey.Save)
        self.actionLoad_Video.setText("Video hinzufügen …")
        self.actionLoad_Video.setShortcut(QKeySequence("Ctrl+Shift+O"))

        self.actionAnalyse_speichern_unter = QAction("Analyse speichern unter …", self)
        self.actionAnalyse_speichern_unter.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.actionAnalyse_schliessen = QAction("Schließen", self)
        self.actionAnalyse_schliessen.setShortcut(QKeySequence.StandardKey.Close)

        self.actionAnalyse_entfernen.triggered.connect(self.new_analysis)
        self.actionAnalyse_laden.triggered.connect(self.open_analysis)
        self.actionAnalyse_speichern.triggered.connect(self.save_analysis)
        self.actionAnalyse_speichern_unter.triggered.connect(self.save_analysis_as)
        self.actionLoad_Video.triggered.connect(self.open_video)
        self.actionAnalyse_schliessen.triggered.connect(self.close)

        self.menuFile.clear()
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

        # Every entry it held has moved into the File menu.
        self.menubar.removeAction(self.menuBearbeiten.menuAction())

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
        self.pending_clip_start = None
        self.disable_clip_handler()
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
        self.titleLabel.setText(analysis.title or UNTITLED_ANALYSIS_LABEL)
        self.treeWidget.render_analysis(analysis)
        self.refresh_document_state()

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
        """Carry each speed as a number, so nothing parses the label text."""
        for index, rate in enumerate(PLAYBACK_RATES[: self.speedBox.count()]):
            self.speedBox.setItemData(index, rate)
        self.apply_playback_rate()

    def apply_playback_rate(self):
        rate = self.speedBox.currentData()
        self.player.set_playback_rate(1.0 if rate is None else float(rate))

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

        Adding footage must never interrupt the video under review. Choosing
        which of several Source videos is active belongs to the Videos sidebar
        tab (issue #15), so until it exists the player stays on the first one.
        """
        if self.active_source_video() is source_video:
            self.load_media(source_video)

    def load_media(self, source_video: SourceVideo):
        self.player.load(source_video.location)

    def active_source_video(self) -> SourceVideo | None:
        source_videos = self.analysis.source_videos
        return source_videos[0] if source_videos else None

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
        """Begin a Pending Clip on the active Source video."""
        self.pending_clip_start = self.player.position()

    def clip_stopped(self):
        self.player.pause()
        clip_stop = self.player.position()
        clip_start = self.pending_clip_start
        self.pending_clip_start = None

        if clip_start is None:
            return
        if self.active_source_video() is None:
            QMessageBox.information(
                self,
                "Kein Video",
                "Ein Clip braucht ein geladenes Video.",
            )
            return

        self.disable_edit_handler()
        self.clipHandler.new_clip(clip_start, clip_stop, self.category_names())
        self.clipHandler.setVisible(True)

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
        source_video = self.active_source_video()
        if source_video is None:
            return

        def add_clip():
            with self.analysis.transaction():
                self.analysis.add_clip(
                    source_video.id,
                    draft.name,
                    draft.start_ms,
                    draft.end_ms,
                    notes=draft.notes,
                    category_id=self.category_id_for(draft.category_name),
                )

        if self.apply_analysis_change(add_clip, "Clip could not be created"):
            self.disable_clip_handler()

    def edit_clip(self, clip_id):
        try:
            clip = self.analysis.clip(clip_id)
        except AnalysisError:
            return
        category_name = (
            None
            if clip.category_id is None
            else self.analysis.category(clip.category_id).name
        )

        self.disable_clip_handler()
        self.editHandler.new_clip(
            ClipItem.from_clip(clip, category_name),
            self.category_names(),
        )
        self.editHandler.setVisible(True)

    def apply_clip_edit(self, draft):
        if draft.clip_id is None:
            return

        def update_clip():
            with self.analysis.transaction():
                self.analysis.update_clip(
                    draft.clip_id,
                    name=draft.name,
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

    def disable_edit_handler(self):
        self.editHandler.setVisible(False)

    def jump_to_clip(self, item, _column=0):
        if not isinstance(item, ClipTreeItem):
            return

        self.player.seek(item.clip_item.start_position)

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
        with QSignalBlocker(self.position_slider):
            self.position_slider.setTracking(True)
            self.position_slider.setSliderPosition(position)
            self.position_slider.update()
            self.position_slider.repaint()
        self.set_position_label(position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)
        self.set_duration_label(duration)

    def set_position_label(self, position):
        self.position_label.setText(f"{milliseconds_to_hhmmss(position)}")

    def set_duration_label(self, duration):
        self.duration_label.setText(f"{milliseconds_to_hhmmss(duration)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
