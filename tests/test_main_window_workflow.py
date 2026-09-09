from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

import mainwindow as mainwindow_module  # noqa: E402
from analysis import UnsavedChangesChoice, new_analysis_document  # noqa: E402
from clip_handler import ClipDraft, ClipHandler  # noqa: E402
from playback import FakePlayback  # noqa: E402
from mainwindow import MainWindow  # noqa: E402
from treewidget import TreeWidget  # noqa: E402
from treewidget_item import ClipTreeItem  # noqa: E402


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
    window.clipHandler.new_clip(start_ms, end_ms, window.category_names())
    window.clipHandler.setVisible(True)
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
    window.jump_to_clip(_clip_rows(window)[0])

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

    window.remove_analysis()

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

    window.remove_analysis()

    assert window.analysis.clips == ()
    assert window.analysis.source_videos == ()
    assert _clip_rows(window) == []
    assert window.is_saved is True


def test_navigating_to_a_clip_seeks_the_player_to_its_start(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    _load_video(window, tmp_path)
    _create_clip(window, start_ms=12_000, end_ms=14_000)

    window.jump_to_clip(_clip_rows(window)[0])

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
    window.remove_analysis()

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
