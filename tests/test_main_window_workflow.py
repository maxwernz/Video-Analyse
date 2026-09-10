from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt, QTime  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtGui import QColor, QKeySequence, QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

import mainwindow as mainwindow_module  # noqa: E402
from analysis import UnsavedChangesChoice, new_analysis_document  # noqa: E402
from clip_handler import ClipDraft, ClipHandler  # noqa: E402
from playback import FakePlayback  # noqa: E402
from mainwindow import MainWindow  # noqa: E402
from treewidget import TreeWidget  # noqa: E402
from treewidget_item import ClipTreeItem  # noqa: E402
from workspace import (  # noqa: E402
    CLIP_COLUMN_LABELS,
    SIDEBAR_WIDTH,
    SOURCE_VIDEO_COLUMN_LABEL,
)


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def silent_message_boxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Keep modal reports out of the tests while still recording them."""
    reported: list[tuple[str, str]] = []

    for level in ("critical", "warning", "information"):
        monkeypatch.setattr(
            QMessageBox,
            level,
            staticmethod(
                lambda _parent, title, text, _level=level, *args, **kwargs: (
                    reported.append((_level, f"{title}: {text}"))
                    or QMessageBox.StandardButton.Ok
                )
            ),
        )
    return reported


@pytest.fixture
def window(application: QApplication):
    main_window = MainWindow(playback=FakePlayback())
    yield main_window
    main_window.document = new_analysis_document()
    main_window.close()


def _load_video(window: MainWindow, tmp_path: Path) -> Path:
    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(b"not a real video")
    window.load_video(str(video_path))
    return video_path


def _category_row(window: MainWindow, name: str):
    for item in window.treeWidget.get_top_level_items():
        if item.text(0) == name:
            return item
    return None


def _clip_rows(window: MainWindow) -> list[ClipTreeItem]:
    rows: list[ClipTreeItem] = []
    for item in window.treeWidget.get_top_level_items():
        if isinstance(item, ClipTreeItem):
            rows.append(item)
        else:
            rows.extend(item.children())
    return rows


def _create_clip(
    window: MainWindow,
    name: str = "Fast break",
    category: str | None = "Angriff",
    start_ms: int = 1_000,
    end_ms: int = 2_000,
) -> None:
    """Mark a Clip the way the transport does: two boundaries, then the form."""
    window.player.seek(start_ms)
    window.clipButton.setChecked(True)
    window.player.seek(end_ms)
    window.clipButton.setChecked(False)
    window.clipHandler.clipNameLine.setText(name)
    window.clipHandler.categoryBox.setCurrentText("" if category is None else category)
    window.clipHandler.acceptButton.click()


def test_widgets_do_not_own_process_wide_clip_or_category_collections() -> None:
    assert not hasattr(TreeWidget, "tree_item_list")
    assert not hasattr(ClipHandler, "categories")


def test_a_new_window_starts_with_an_empty_saved_analysis(window: MainWindow) -> None:
    assert window.analysis.source_videos == ()
    assert window.analysis.clips == ()
    assert window.is_saved is True
    assert _clip_rows(window) == []


def test_a_category_without_clips_is_still_rendered(window: MainWindow) -> None:
    assert [
        item.text(0) for item in window.treeWidget.get_top_level_items()
    ] == ["Abwehr", "Angriff", "Tor"]


def test_loading_a_video_adds_a_source_video_and_dirties_the_document(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    video_path = _load_video(window, tmp_path)

    assert [source.location for source in window.analysis.source_videos] == [
        str(video_path)
    ]
    assert window.analysis.title == "first-half"
    assert window.titleLabel.text() == "first-half"
    assert window.is_saved is False


def test_creating_a_clip_goes_through_the_analysis_and_is_rendered(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)

    _create_clip(window, name="Fast break", category="Angriff")

    clip = window.analysis.clips[0]
    assert clip.name == "Fast break"
    assert clip.start_ms == 1_000
    assert clip.end_ms == 2_000
    assert window.analysis.category(clip.category_id).name == "Angriff"
    assert window.clipHandler.isVisibleTo(window) is False

    category_item = _category_row(window, "Angriff")
    assert category_item.child(0).clip_id == clip.id


def test_an_unknown_category_name_creates_one_category(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)

    _create_clip(window, name="Fast break", category="Konter")
    _create_clip(window, name="Second", category="Konter", start_ms=3_000, end_ms=4_000)

    assert [category.name for category in window.analysis.categories].count("Konter") == 1


def test_editing_a_clip_updates_the_analysis_in_place(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]

    window.edit_clip(clip.id)
    assert window.editHandler.isVisibleTo(window) is True
    window.editHandler.clipNameLine.setText("Fast break finish")
    window.editHandler.notesText.setText("Left wing")
    window.editHandler.categoryBox.setCurrentText("Abwehr")
    window.editHandler.acceptButton.click()

    updated = window.analysis.clip(clip.id)
    assert updated.name == "Fast break finish"
    assert updated.notes == "Left wing"
    assert window.analysis.category(updated.category_id).name == "Abwehr"
    assert len(window.analysis.clips) == 1
    assert window.editHandler.isVisibleTo(window) is False
    assert _category_row(window, "Abwehr").child(0).clip_id == clip.id
    assert _category_row(window, "Angriff").childCount() == 0


def _set_boundaries(handler: ClipHandler, start_ms: int, end_ms: int) -> None:
    """Type new boundaries into the editing form, the way a person does."""
    handler.startTimeEdit.setTime(QTime.fromMSecsSinceStartOfDay(start_ms))
    handler.endTimeEdit.setTime(QTime.fromMSecsSinceStartOfDay(end_ms))


def test_editing_a_clips_boundaries_moves_it_in_the_analysis(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """The boundaries are part of the form, and the Analysis accepts them."""
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]

    window.edit_clip(clip.id)
    _set_boundaries(window.editHandler, 4_000, 9_500)
    window.editHandler.acceptButton.click()

    updated = window.analysis.clip(clip.id)
    assert (updated.start_ms, updated.end_ms) == (4_000, 9_500)
    assert updated.name == clip.name
    assert window.editHandler.isVisibleTo(window) is False


def test_boundaries_the_model_rejects_are_reported_and_change_nothing(
    window: MainWindow,
    tmp_path: Path,
    silent_message_boxes: list[tuple[str, str]],
) -> None:
    """The interval invariant is the Analysis's; the form only reports it."""
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]

    window.edit_clip(clip.id)
    _set_boundaries(window.editHandler, 9_000, 4_000)
    window.editHandler.acceptButton.click()

    assert window.analysis.clip(clip.id) == clip
    assert any(level == "critical" for level, _ in silent_message_boxes)
    assert window.editHandler.isVisibleTo(window) is True


def test_cancelling_an_edit_leaves_the_clip_and_the_workspace_as_they_were(
    window: MainWindow,
    tmp_path: Path,
    application: QApplication,
) -> None:
    """Leaving the editing state gives the video area its full width back."""
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]
    window.resize(1280, 720)
    window.show()

    window.edit_clip(clip.id)
    window.editHandler.clipNameLine.setText("Never applied")
    _set_boundaries(window.editHandler, 4_000, 9_500)
    window.editHandler.cancelButton.click()
    application.processEvents()

    assert window.analysis.clip(clip.id) == clip
    assert window.editHandler.isVisibleTo(window) is False
    assert window.clipEditorArea.width() == 0


def test_editing_a_clip_from_the_clips_tab_opens_the_paused_editing_state(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """One editor serves both paths, and it keeps a paused frame beside it."""
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]
    window.player.play()

    window.treeWidget.clip_edit_requested.emit(clip.id)

    assert window.player.is_playing() is False
    assert window.playPauseButton.isChecked() is False
    assert window.editHandler.isVisibleTo(window) is True
    assert window.editHandler.clip_id == clip.id


def test_editing_an_existing_clip_abandons_a_clip_that_was_only_marked(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """The workspace is in one editing state at a time, and the record control
    says so."""
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]
    window.player.seek(30_000)
    window.clipButton.setChecked(True)

    window.treeWidget.clip_edit_requested.emit(clip.id)

    assert window.pending_clip is None
    assert window.clipButton.isChecked() is False
    assert window.clipHandler.isVisibleTo(window) is False
    assert window.editHandler.isVisibleTo(window) is True


def test_the_editing_form_carries_the_whole_clip(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """Title, Category, both boundaries and notes all survive the round trip."""
    _load_video(window, tmp_path)
    _create_clip(window, name="Fast break", category="Angriff")
    clip = window.analysis.clips[0]

    window.edit_clip(clip.id)
    window.editHandler.notesText.setText("Left wing")
    _set_boundaries(window.editHandler, 4_000, 9_500)
    window.editHandler.acceptButton.click()

    window.edit_clip(clip.id)
    form = window.editHandler
    assert form.clipNameLine.text() == "Fast break"
    assert form.categoryBox.currentText() == "Angriff"
    assert (form.start_time, form.stop_time) == (4_000, 9_500)
    assert form.notesText.toPlainText() == "Left wing"


def test_an_invalid_clip_edit_is_reported_and_changes_nothing(
    window: MainWindow,
    tmp_path: Path,
    silent_message_boxes: list[tuple[str, str]],
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]

    window.apply_clip_edit(
        ClipDraft(
            name="   ",
            notes="",
            category_name=None,
            start_ms=clip.start_ms,
            end_ms=clip.end_ms,
            clip_id=clip.id,
        )
    )

    assert window.analysis.clip(clip.id) == clip
    assert any(level == "critical" for level, _ in silent_message_boxes)


def test_a_rejected_clip_change_leaves_the_document_as_it_was(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    _save_to(window, tmp_path / "match.analysis", monkeypatch)
    clip = window.analysis.clips[0]

    window.apply_clip_edit(
        ClipDraft(
            name="   ",
            notes="",
            category_name="Konter",
            start_ms=clip.start_ms,
            end_ms=clip.end_ms,
            clip_id=clip.id,
        )
    )

    assert window.analysis.category_named("Konter") is None
    assert window.document.dirty is False
    assert window.is_saved is True


def test_removing_a_clip_removes_it_from_the_analysis(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]

    window.remove_clip(clip.id)

    assert window.analysis.clips == ()
    assert _clip_rows(window) == []


def test_removing_a_category_keeps_its_clips_uncategorized(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    clip = window.analysis.clips[0]

    window.remove_category(clip.category_id)

    assert window.analysis.clip(clip.id).category_id is None
    assert _category_row(window, "Angriff") is None
    rendered = _clip_rows(window)[0]
    assert rendered.parent() is None
    assert rendered.clip_id == clip.id


def test_renaming_the_analysis_retitles_it_without_touching_its_identity(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    analysis_id = window.analysis.id
    monkeypatch.setattr(
        mainwindow_module.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("Spiel gegen Musterstadt", True)),
    )

    window.rename_analysis()

    assert window.analysis.title == "Spiel gegen Musterstadt"
    assert window.analysis.id == analysis_id
    assert window.titleLabel.text() == "Spiel gegen Musterstadt"


def test_playback_position_and_selection_do_not_dirty_the_document(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    _save_to(window, tmp_path / "match.analysis", monkeypatch)
    assert window.is_saved is True

    window.position_changed(4_200)
    window.duration_changed(90_000)
    _clip_rows(window)[0].setSelected(True)
    window.treeWidget.sortByColumn(0, mainwindow_module.Qt.DescendingOrder)
    window.treeWidget.collapseAll()
    window.navigate_to_clip(_clip_rows(window)[0].clip_id)

    assert window.document.dirty is False
    assert window.is_saved is True


def _save_to(
    window: MainWindow,
    path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(path), "")),
    )
    assert window.save_analysis() is True


def test_saving_and_reopening_preserves_identities_and_content(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    analysis_id = window.analysis.id
    clip_id = window.analysis.clips[0].id
    analysis_path = tmp_path / "match.analysis"

    _save_to(window, analysis_path, monkeypatch)

    assert window.is_saved is True
    assert analysis_path.read_bytes().lstrip().startswith(b"{")

    window.document = new_analysis_document()
    window.load_analysis(str(analysis_path))

    assert window.analysis.id == analysis_id
    assert [clip.id for clip in window.analysis.clips] == [clip_id]
    assert window.analysis.clips[0].name == "Fast break"
    assert window.document.dirty is False
    assert _category_row(window, "Angriff").child(0).clip_id == clip_id


def test_a_cancelled_save_prevents_close_and_keeps_unsaved_work(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    monkeypatch.setattr(
        window,
        "ask_unsaved_changes",
        lambda: UnsavedChangesChoice.SAVE,
    )
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: ("", "")),
    )

    assert window.may_replace_analysis() is False
    assert window.document.dirty is True
    assert len(window.analysis.clips) == 1


def test_cancelling_the_prompt_keeps_the_current_analysis_loaded(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    monkeypatch.setattr(
        window,
        "ask_unsaved_changes",
        lambda: UnsavedChangesChoice.CANCEL,
    )

    window.new_analysis()

    assert len(window.analysis.clips) == 1
    assert len(_clip_rows(window)) == 1


def test_discarding_starts_a_new_empty_analysis(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    monkeypatch.setattr(
        window,
        "ask_unsaved_changes",
        lambda: UnsavedChangesChoice.DISCARD,
    )

    window.new_analysis()

    assert window.analysis.clips == ()
    assert window.analysis.source_videos == ()
    assert _clip_rows(window) == []
    assert window.is_saved is True


def _menu_texts(window: MainWindow) -> list[str]:
    return [
        action.text()
        for action in window.menuFile.actions()
        if not action.isSeparator()
    ]


def test_the_document_commands_have_menu_entries_and_shortcuts(
    window: MainWindow,
) -> None:
    commands = {
        window.actionAnalyse_entfernen: QKeySequence.StandardKey.New,
        window.actionAnalyse_laden: QKeySequence.StandardKey.Open,
        window.actionAnalyse_speichern: QKeySequence.StandardKey.Save,
        window.actionAnalyse_speichern_unter: QKeySequence.StandardKey.SaveAs,
        window.actionAnalyse_schliessen: QKeySequence.StandardKey.Close,
    }
    menu_texts = _menu_texts(window)

    for action, standard_key in commands.items():
        assert action.shortcut() == QKeySequence(standard_key)
        assert action.text() in menu_texts

    assert window.actionLoad_Video.text() in menu_texts
    assert window.actionLoad_Video.shortcut() == QKeySequence("Ctrl+Shift+O")


def test_adding_a_second_video_keeps_the_first_and_its_clips(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    second_video = tmp_path / "second-half.mp4"
    second_video.write_bytes(b"not a real video")

    window.load_video(str(second_video))

    assert [source.display_name for source in window.analysis.source_videos] == [
        "first-half.mp4",
        "second-half.mp4",
    ]
    assert len(window.analysis.clips) == 1
    assert window.analysis.title == "first-half"


def test_a_dropped_video_is_added_to_the_current_analysis(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    dropped = tmp_path / "second-half.MOV"
    dropped.write_bytes(b"not a real video")

    assert window.drop_file(str(dropped)) is True

    assert len(window.analysis.source_videos) == 2


def test_a_dropped_file_of_another_kind_is_ignored(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    note = tmp_path / "notes.txt"
    note.write_text("nothing to see", encoding="utf-8")

    assert window.drop_file(str(note)) is False
    assert window.analysis.source_videos == ()


def test_the_window_title_reports_the_analysis_and_its_dirty_state(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert window.windowTitle() == "Unbenannte Analyse — Video Analyse"

    _load_video(window, tmp_path)
    assert window.windowTitle() == "• first-half — Video Analyse"

    _save_to(window, tmp_path / "match.analysis", monkeypatch)
    assert window.windowTitle() == "first-half — Video Analyse"

    _create_clip(window)
    assert window.windowTitle() == "• first-half — Video Analyse"


def test_save_as_writes_the_analysis_to_a_second_file(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    _save_to(window, tmp_path / "match.analysis", monkeypatch)

    copy_path = tmp_path / "copy.analysis"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(copy_path), "")),
    )
    assert window.save_analysis_as() is True

    assert copy_path.is_file()
    assert window.document.path == copy_path
    assert window.is_saved is True


def test_a_failed_open_leaves_the_current_analysis_untouched(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    silent_message_boxes: list[tuple[str, str]],
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    analysis = window.analysis
    broken = tmp_path / "broken.analysis"
    broken.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(
        window,
        "ask_unsaved_changes",
        lambda: UnsavedChangesChoice.DISCARD,
    )

    assert window.load_analysis(str(broken)) is False

    assert window.analysis is analysis
    assert len(window.analysis.clips) == 1
    assert len(_clip_rows(window)) == 1
    assert any(level == "critical" for level, _ in silent_message_boxes)


def test_adding_a_video_does_not_interrupt_the_one_under_review(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    first_video = _load_video(window, tmp_path)
    second_video = tmp_path / "second-half.mp4"
    second_video.write_bytes(b"not a real video")

    window.load_video(str(second_video))

    first = window.analysis.source_videos[0]
    assert first.location == str(first_video)
    assert window.active_source_video() == first

    _create_clip(window, name="Fast break")
    assert window.analysis.clips[0].source_video_id == first.id


def test_navigating_to_a_clip_seeks_the_player_to_its_start(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window, start_ms=12_000, end_ms=14_000)

    _click_clip_row(window, "Fast break")

    assert window.player.position() == 12_000


def test_a_clip_is_marked_against_the_player_position(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    window.player.play()
    window.player.seek(30_000)
    window.clip_started()
    window.player.seek(35_000)

    window.clip_stopped()

    assert window.player.is_playing() is False
    assert window.clipHandler.isVisibleTo(window) is True
    assert (window.clipHandler.start_time, window.clipHandler.stop_time) == (
        30_000,
        35_000,
    )


def test_the_play_button_follows_what_the_player_is_actually_doing(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)

    window.player.play()
    assert window.playPauseButton.isChecked() is True

    window.player.step_backward()
    assert window.playPauseButton.isChecked() is False


def test_choosing_a_playback_speed_sets_a_numeric_rate(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)

    window.speedBox.setCurrentText("0.25x")

    assert window.player.playback_rate() == 0.25


def test_loading_a_video_makes_it_the_active_source_video_of_the_player(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_path = _load_video(window, tmp_path)

    assert window.player.is_loaded() is True
    assert window.player.location() == str(video_path)

    monkeypatch.setattr(
        window,
        "ask_unsaved_changes",
        lambda: UnsavedChangesChoice.DISCARD,
    )
    window.new_analysis()

    assert window.player.is_loaded() is False


def test_playing_stepping_and_speed_never_dirty_the_document(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window)
    _save_to(window, tmp_path / "match.analysis", monkeypatch)

    window.player.play()
    window.player.seek(20_000)
    window.player.step_forward()
    window.player.step_backward()
    window.speedBox.setCurrentText("2x")
    window.player.play_pause()

    assert window.document.dirty is False
    assert window.is_saved is True


def test_the_play_button_does_not_claim_to_play_with_no_video_loaded(
    window: MainWindow,
) -> None:
    window.playPauseButton.click()

    assert window.player.is_playing() is False
    assert window.playPauseButton.isChecked() is False


def test_the_workspace_is_composed_in_code_without_the_designer_window() -> None:
    """The Designer main window is retired; see ADR 0005."""
    repository_root = Path(mainwindow_module.__file__).parent

    assert importlib.util.find_spec("Ui_main_window") is None
    assert not (repository_root / "main_window.ui").exists()
    assert not (repository_root / "Ui_main_window.py").exists()


def test_an_analysis_without_source_videos_renders_the_normal_workspace(
    window: MainWindow,
) -> None:
    """There is no separate welcome screen; only the player's place changes."""
    assert window.analysis.source_videos == ()

    assert [
        window.sidebarTabs.tabText(index)
        for index in range(window.sidebarTabs.count())
    ] == ["Clips", "Videos"]
    assert window.sidebar.isVisibleTo(window) is True
    assert window.timelineArea.isVisibleTo(window) is True
    assert window.playerStack.currentWidget() is window.emptyPlayerHint


def test_the_call_to_action_adds_a_video_and_gives_way_to_the_player(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(b"not a real video")
    monkeypatch.setattr(window, "choose_source_video", lambda: str(video_path))

    window.addVideoButton.click()

    assert [source.location for source in window.analysis.source_videos] == [
        str(video_path)
    ]
    assert window.playerStack.currentWidget() is window.videoWidget


def _corner_in_window(window: MainWindow, widget) -> QPoint:
    return widget.mapTo(window, QPoint(0, 0))


def test_the_workspace_lays_the_areas_out_as_the_validated_direction_asks(
    window: MainWindow,
    application: QApplication,
) -> None:
    """Sidebar left of the video, compact timeline directly beneath it."""
    window.resize(1280, 720)
    window.show()
    application.processEvents()

    sidebar = _corner_in_window(window, window.sidebar)
    video = _corner_in_window(window, window.playerStack)
    timeline = _corner_in_window(window, window.timelineArea)

    assert sidebar.x() + window.sidebar.width() <= video.x()
    assert timeline.y() >= video.y() + window.playerStack.height()
    assert window.timelineArea.height() < window.playerStack.height()
    assert window.height() <= 720 and window.width() <= 1280


def test_the_workspace_stays_usable_at_a_small_laptop_size(
    window: MainWindow,
) -> None:
    """It opens at that size, and stays usable when made smaller still."""
    assert window.size().width() <= 1280
    assert window.size().height() <= 720
    assert window.minimumSizeHint().width() <= 1280
    assert window.minimumSizeHint().height() <= 720


def test_the_clip_editing_state_takes_its_room_beside_the_video(
    window: MainWindow,
    tmp_path: Path,
    application: QApplication,
) -> None:
    """During normal review the editing area takes none of the video's width."""
    _load_video(window, tmp_path)
    window.resize(1280, 720)
    window.show()
    application.processEvents()
    assert window.clipEditorArea.width() == 0

    window.player.seek(30_000)
    window.clip_started()
    window.player.seek(35_000)
    window.clip_stopped()
    application.processEvents()

    assert window.clipHandler.isVisibleTo(window) is True
    assert window.clipEditorArea.width() > 0
    assert _corner_in_window(window, window.clipEditorArea).x() >= (
        _corner_in_window(window, window.playerStack).x() + window.playerStack.width()
    )


def test_the_timeline_area_reports_where_the_player_is(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    window.duration_changed(5_400_000)

    window.player.seek(12_000)

    assert window.position_label.text() == "00:00:12"
    assert window.duration_label.text() == "01:30:00"


def test_a_category_color_is_rendered_muted_without_changing_the_analysis(
    window: MainWindow,
) -> None:
    """Color informs; the Category name and the selection carry the meaning."""
    category = window.analysis.category_named("Angriff")
    rendered = _category_row(window, "Angriff").foreground(0).color()

    assert rendered.saturation() < QColor(category.color).saturation()
    assert category.color == "#EF4444"


TIMELINE_WIDTH = 600
"""The width the timeline tests scrub across, so pixels map to round times."""


def _timeline_at(window: MainWindow, x: int) -> QPoint:
    """A point on the timeline, at a width both platforms agree on."""
    window.timeline.resize(TIMELINE_WIDTH, window.timeline.height())
    return QPoint(x, window.timeline.height() // 2)


def _timeline_click(window: MainWindow, x: int) -> None:
    QTest.mouseClick(
        window.timeline, Qt.MouseButton.LeftButton, pos=_timeline_at(window, x)
    )


def _prepared_timeline(
    window: MainWindow,
    tmp_path: Path,
    duration_ms: int = 60_000,
) -> None:
    _load_video(window, tmp_path)
    window.player.set_duration(duration_ms)


def test_the_timeline_shows_the_clips_of_the_active_source_video_only(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _prepared_timeline(window, tmp_path)
    _create_clip(window, name="Fast break", start_ms=30_000, end_ms=40_000)
    second_video = tmp_path / "second-half.mp4"
    second_video.write_bytes(b"not a real video")
    window.load_video(str(second_video))
    first, second = window.analysis.source_videos

    window.activate_source_video(second.id)

    assert window.active_source_video() == second
    assert window.timeline.range_at(_timeline_at(window, 350).x()) is None

    window.activate_source_video(first.id)
    window.player.set_duration(60_000)

    on_timeline = window.timeline.range_at(_timeline_at(window, 350).x())
    assert on_timeline is not None
    assert on_timeline.clip_id == window.analysis.clips[0].id


def test_clicking_the_timeline_scrubs_the_player_to_that_time(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _prepared_timeline(window, tmp_path)

    _timeline_click(window, TIMELINE_WIDTH // 2)

    assert window.player.position() == 30_000


def test_clicking_a_clip_range_selects_it_without_moving_the_playhead(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _prepared_timeline(window, tmp_path)
    _create_clip(window, name="Fast break", start_ms=30_000, end_ms=40_000)

    _timeline_click(window, 350)

    clip = window.analysis.clips[0]
    assert window.selected_clip() == clip
    assert window.player.position() == 35_000
    assert "Fast break" in window.selectedClipLabel.text()
    assert "00:00:30" in window.selectedClipLabel.text()
    assert "00:00:40" in window.selectedClipLabel.text()


def test_double_clicking_a_clip_range_seeks_to_the_clip_start(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _prepared_timeline(window, tmp_path)
    _create_clip(window, start_ms=30_000, end_ms=40_000)

    QTest.mouseDClick(
        window.timeline, Qt.MouseButton.LeftButton, pos=_timeline_at(window, 350)
    )

    assert window.player.position() == 30_000
    assert window.selected_clip() == window.analysis.clips[0]


def test_navigating_to_a_clip_activates_its_source_video_and_the_timeline_follows(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """The seam the Clips sidebar tab (#15) navigates through."""
    _prepared_timeline(window, tmp_path)
    second_video = tmp_path / "second-half.mp4"
    second_video.write_bytes(b"not a real video")
    window.load_video(str(second_video))
    second = window.analysis.source_videos[1]
    window.analysis.add_clip(second.id, "Counter", 20_000, 25_000)
    window.render_analysis()

    window.navigate_to_clip(window.analysis.clips[0].id)

    assert window.active_source_video() == second
    assert window.player.location() == str(second_video)
    assert window.player.position() == 20_000
    assert window.timeline.selected_clip_id() == window.analysis.clips[0].id
    window.player.set_duration(60_000)
    shown = window.timeline.range_at(_timeline_at(window, 220).x())
    assert shown is not None and shown.clip_id == window.analysis.clips[0].id


def test_the_timeline_never_dirties_the_analysis_document(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selection and playhead are transient, exactly like playback state."""
    _prepared_timeline(window, tmp_path)
    _create_clip(window, start_ms=30_000, end_ms=40_000)
    _save_to(window, tmp_path / "match.analysis", monkeypatch)
    assert window.is_saved is True

    _timeline_click(window, 350)
    QTest.mouseDClick(
        window.timeline, Qt.MouseButton.LeftButton, pos=_timeline_at(window, 350)
    )
    window.activate_source_video(window.analysis.source_videos[0].id)

    assert window.document.dirty is False
    assert window.is_saved is True


def test_navigating_within_the_active_source_video_does_not_reload_it(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """Reloading would drop the frame under review and the known duration."""
    _prepared_timeline(window, tmp_path)
    _create_clip(window, start_ms=30_000, end_ms=40_000)

    window.navigate_to_clip(window.analysis.clips[0].id)

    assert window.player.duration() == 60_000
    assert window.player.position() == 30_000


def _drag_timeline_to(window: MainWindow, x: int) -> None:
    """One move of a held drag; ``QTest.mouseMove`` carries no button state."""
    position = QPointF(_timeline_at(window, x))
    QApplication.sendEvent(
        window.timeline,
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            position,
            QPointF(window.timeline.mapToGlobal(_timeline_at(window, x))),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )


def test_dragging_along_the_timeline_scrubs_the_player_continuously(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _prepared_timeline(window, tmp_path)

    QTest.mousePress(
        window.timeline, Qt.MouseButton.LeftButton, pos=_timeline_at(window, 60)
    )
    assert window.player.position() == 6_000

    _drag_timeline_to(window, 300)
    assert window.player.position() == 30_000

    QTest.mouseRelease(
        window.timeline, Qt.MouseButton.LeftButton, pos=_timeline_at(window, 300)
    )
    assert window.player.position() == 30_000


class LateDurationPlayback(FakePlayback):
    """Media that still reports the previous length just after it is loaded.

    Real media behaves this way: the player announces the new duration a
    moment after its source is set.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stale_duration = 0

    def load(self, location: str) -> None:
        previous_duration = self.duration()
        super().load(location)
        self._stale_duration = previous_duration

    def set_duration(self, duration_ms: int) -> None:
        self._stale_duration = 0
        super().set_duration(duration_ms)

    def duration(self) -> int:
        return self._stale_duration or super().duration()


def test_a_previous_source_videos_length_never_scales_the_active_one(
    application: QApplication,
    tmp_path: Path,
) -> None:
    """The timeline draws no time scale until the player reports one."""
    window = MainWindow(playback=LateDurationPlayback())
    try:
        first_video = _load_video(window, tmp_path)
        window.player.set_duration(5_400_000)
        second_video = tmp_path / "second-half.mp4"
        second_video.write_bytes(b"not a real video")
        window.load_video(str(second_video))
        assert first_video.exists()

        window.activate_source_video(window.analysis.source_videos[1].id)

        assert window.player.duration() == 5_400_000
        assert window.timeline.duration() == 0
        assert window.duration_label.text() == "00:00:00"
    finally:
        window.document = new_analysis_document()
        window.close()


# --- The Clips and Videos sidebar (#15) -----------------------------------


SIDEBAR_LIST_SIZE = (SIDEBAR_WIDTH, 240)


def _add_video(window: MainWindow, tmp_path: Path, name: str) -> Path:
    video_path = tmp_path / name
    video_path.write_bytes(b"not a real video")
    window.load_video(str(video_path))
    return video_path


def _video_rows(window: MainWindow) -> list[str]:
    videos = window.sourceVideoList
    return [videos.item(row).text() for row in range(videos.count())]


def _click_video_row(window: MainWindow, row: int) -> None:
    """Select a Source video the way a person does, at a size both platforms agree on."""
    videos = window.sourceVideoList
    videos.resize(*SIDEBAR_LIST_SIZE)
    QTest.mouseClick(
        videos.viewport(),
        Qt.MouseButton.LeftButton,
        pos=videos.visualItemRect(videos.item(row)).center(),
    )


def test_the_videos_tab_lists_every_source_video_of_the_analysis(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _add_video(window, tmp_path, "second-half.mp4")

    assert window.videosTab.isAncestorOf(window.sourceVideoList)
    assert _video_rows(window) == ["first-half.mp4", "second-half.mp4"]


def test_selecting_a_source_video_switches_the_player_to_it(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    second_video = _add_video(window, tmp_path, "second-half.mp4")

    _click_video_row(window, 1)

    assert window.active_source_video() == window.analysis.source_videos[1]
    assert window.player.location() == str(second_video)


def test_moving_through_the_videos_tab_by_keyboard_switches_the_player(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    second_video = _add_video(window, tmp_path, "second-half.mp4")
    videos = window.sourceVideoList
    videos.resize(*SIDEBAR_LIST_SIZE)

    QTest.keyClick(videos, Qt.Key.Key_Down)

    assert window.active_source_video() == window.analysis.source_videos[1]
    assert window.player.location() == str(second_video)


def test_marking_a_clip_without_a_video_leaves_the_transport_honest(
    window: MainWindow,
    silent_message_boxes: list[tuple[str, str]],
) -> None:
    window.clipButton.setChecked(True)

    assert window.pending_clip is None
    assert window.clipButton.isChecked() is False
    assert any(level == "information" for level, _ in silent_message_boxes)


def test_each_clip_row_names_the_source_video_it_belongs_to(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """The cue that keeps the Clips tab readable while Videos is not visible."""
    _load_video(window, tmp_path)
    _create_clip(window, name="Fast break")
    _add_video(window, tmp_path, "second-half.mp4")
    window.activate_source_video(window.analysis.source_videos[1].id)
    _create_clip(window, name="Counter", start_ms=3_000, end_ms=4_000)

    cue = CLIP_COLUMN_LABELS.index(SOURCE_VIDEO_COLUMN_LABEL)
    assert {row.text(0): row.text(cue) for row in _clip_rows(window)} == {
        "Fast break": "first-half.mp4",
        "Counter": "second-half.mp4",
    }


def _click_clip_row(window: MainWindow, name: str) -> None:
    """Choose a Clip the way a person does, at a size both platforms agree on."""
    clips = window.treeWidget
    clips.resize(*SIDEBAR_LIST_SIZE)
    row = next(item for item in _clip_rows(window) if item.text(0) == name)
    QTest.mouseClick(
        clips.viewport(),
        Qt.MouseButton.LeftButton,
        pos=clips.visualItemRect(row).center(),
    )


def test_selecting_a_clip_in_the_clips_tab_activates_its_source_video(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    first_video = _load_video(window, tmp_path)
    _create_clip(window, name="Fast break", start_ms=12_000, end_ms=14_000)
    _add_video(window, tmp_path, "second-half.mp4")
    window.activate_source_video(window.analysis.source_videos[1].id)

    _click_clip_row(window, "Fast break")

    assert window.active_source_video() == window.analysis.source_videos[0]
    assert window.player.location() == str(first_video)
    assert window.player.position() == 12_000
    assert window.selected_clip() == window.analysis.clips[0]


def test_a_new_clip_is_bound_to_the_source_video_it_was_marked_on(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _add_video(window, tmp_path, "second-half.mp4")
    second = window.analysis.source_videos[1]
    window.activate_source_video(second.id)

    _create_clip(window, name="Counter", start_ms=10_000, end_ms=12_000)

    clip = window.analysis.clips[0]
    assert clip.source_video_id == second.id
    assert (clip.start_ms, clip.end_ms) == (10_000, 12_000)


def test_a_pending_clip_cannot_produce_a_clip_on_another_source_video(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    """A Pending Clip belongs to the Source video its start was marked on."""
    _load_video(window, tmp_path)
    _add_video(window, tmp_path, "second-half.mp4")
    window.player.seek(30_000)
    window.clipButton.setChecked(True)

    _click_video_row(window, 1)
    window.player.seek(5_000)
    window.clipButton.setChecked(False)

    assert window.analysis.clips == ()
    assert window.clipHandler.isVisibleTo(window) is False
    assert window.clipButton.isChecked() is False


def test_switching_source_video_discards_a_clip_that_was_never_created(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _add_video(window, tmp_path, "second-half.mp4")
    window.player.seek(30_000)
    window.clipButton.setChecked(True)
    window.player.seek(35_000)
    window.clipButton.setChecked(False)
    assert window.clipHandler.isVisibleTo(window) is True

    _click_video_row(window, 1)

    assert window.clipHandler.isVisibleTo(window) is False
    window.clipHandler.clipNameLine.setText("Counter")
    window.clipHandler.acceptButton.click()
    assert window.analysis.clips == ()


def test_cancelling_a_marked_clip_leaves_nothing_behind(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    window.player.seek(30_000)
    window.clipButton.setChecked(True)
    window.player.seek(35_000)
    window.clipButton.setChecked(False)

    window.clipHandler.cancelButton.click()

    assert window.analysis.clips == ()
    assert window.clipHandler.isVisibleTo(window) is False
    assert window.clipButton.isChecked() is False
    assert window.pending_clip is None


def test_several_source_videos_and_their_clips_survive_save_and_reopen(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_video = _load_video(window, tmp_path)
    _create_clip(window, name="Fast break")
    second_video = _add_video(window, tmp_path, "second-half.mp4")
    window.activate_source_video(window.analysis.source_videos[1].id)
    _create_clip(window, name="Counter", start_ms=10_000, end_ms=12_000)
    belongs_to = {
        clip.name: window.analysis.source_video(clip.source_video_id).display_name
        for clip in window.analysis.clips
    }
    analysis_path = tmp_path / "match.analysis"
    _save_to(window, analysis_path, monkeypatch)

    window.document = new_analysis_document()
    window.load_analysis(str(analysis_path))

    assert [Path(source.location) for source in window.analysis.source_videos] == [
        first_video,
        second_video,
    ]
    assert {
        clip.name: window.analysis.source_video(clip.source_video_id).display_name
        for clip in window.analysis.clips
    } == belongs_to
    cue = CLIP_COLUMN_LABELS.index(SOURCE_VIDEO_COLUMN_LABEL)
    assert {row.text(0): row.text(cue) for row in _clip_rows(window)} == belongs_to


def test_the_sidebar_tab_and_the_active_source_video_are_never_stored(
    window: MainWindow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Display state is not analytical work: it neither dirties nor persists."""
    _load_video(window, tmp_path)
    _create_clip(window, name="Fast break")
    _add_video(window, tmp_path, "second-half.mp4")
    analysis_path = tmp_path / "match.analysis"
    _save_to(window, analysis_path, monkeypatch)
    assert window.is_saved is True

    window.sidebarTabs.setCurrentWidget(window.videosTab)
    _click_video_row(window, 1)
    window.treeWidget.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    _click_clip_row(window, "Fast break")

    assert window.document.dirty is False
    assert window.is_saved is True

    window.document = new_analysis_document()
    window.load_analysis(str(analysis_path))

    assert window.active_source_video() == window.analysis.source_videos[0]
    assert window.player.location() == window.analysis.source_videos[0].location
