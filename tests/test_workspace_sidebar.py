"""The Clips and Videos lists, as an analyst reads and uses them.

The sidebar is two lists over the same Analysis: every Clip across every
Source video, grouped by Category, and every Source video with the active one
marked. Both are projections computed in Python — the grouping, the ordering,
the timecodes and the Source-video cue are rules about the Analysis, and a
`ListView` delegate is no place for any of them.

Everything here is driven through the view model, which is the one seam, so
none of it needs a window. What a window is needed for — that a row is a hit
target and that clicking one navigates — is in `tests/test_qml_sidebar.py`.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
from analysis import Analysis, AnalysisDocument, Clip  # noqa: E402
from playback import FakePlayback  # noqa: E402
from sidebar_models import UNCATEGORIZED_LABEL, source_badges  # noqa: E402
from workspace_view_model import PRIMING_MS, WorkspaceViewModel  # noqa: E402


FIRST_HALF = "/videos/halbzeit-1.mp4"
SECOND_HALF = "/videos/halbzeit-2.mp4"
FIRST_HALF_MS = 45 * 60_000
SECOND_HALF_MS = 42 * 60_000 + 30_000


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class Scheduler:
    """The event loop, stood in for, so priming is not a wait."""

    def __init__(self) -> None:
        self.pending: list[tuple[int, object]] = []

    def __call__(self, delay_ms: int, run) -> None:  # type: ignore[no-untyped-def]
        self.pending.append((delay_ms, run))

    def elapse(self) -> None:
        due, self.pending = self.pending, []
        for _, run in due:
            run()  # type: ignore[operator]


@pytest.fixture
def scheduler() -> Scheduler:
    return Scheduler()


@pytest.fixture
def analysis() -> Analysis:
    """The canonical fixture's shape: two halves, several Categories."""

    analysis = Analysis("SG Beispiel - TV Muster")
    analysis.add_source_video("halbzeit-1.mp4", FIRST_HALF, duration_ms=FIRST_HALF_MS)
    analysis.add_source_video("halbzeit-2.mp4", SECOND_HALF, duration_ms=SECOND_HALF_MS)
    analysis.add_category("Tore", color="#E2564A")
    analysis.add_category("Abwehr", color="#4BA46A")
    return analysis


@pytest.fixture
def document(analysis: Analysis) -> AnalysisDocument:
    return AnalysisDocument(analysis)


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    return FakePlayback()


@pytest.fixture
def workspace(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> WorkspaceViewModel:
    model = WorkspaceViewModel(document, player, schedule=scheduler)
    scheduler.elapse()
    return model


def a_clip(
    analysis: Analysis,
    *,
    name: str = "Tor",
    start_ms: int = 10_000,
    end_ms: int | None = None,
    category: str | None = None,
    half: int = 0,
) -> Clip:
    category_id = None
    if category is not None:
        found = analysis.category_named(category)
        assert found is not None, category
        category_id = found.id
    return analysis.add_clip(
        analysis.source_videos[half].id,
        name,
        start_ms,
        start_ms + 18_000 if end_ms is None else end_ms,
        category_id=category_id,
    )


def rows(workspace: WorkspaceViewModel) -> tuple:
    return workspace.clipModel.rows()


def clip_rows(workspace: WorkspaceViewModel) -> list:
    return [row for row in rows(workspace) if row["kind"] == "clip"]


def videos(workspace: WorkspaceViewModel) -> tuple:
    return workspace.sourceModel.rows()


def _result(call):  # type: ignore[no-untyped-def]
    """Run a continuation-based `WorkspaceViewModel` command and read its outcome.

    Every document command became fire-and-forget from QML's side with
    issue #69; a workspace built with no presenter (`_NobodyToAsk`) or a
    fake that answers in-line still settles its completion before this
    returns.
    """

    results: list[object] = []
    call(results.append)
    assert results, "the command's completion was never called"
    return results[0]


# --- The Clip list, grouped by Category -------------------------------------


def test_the_clip_list_carries_every_clip_of_every_source_video(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    """One list for the whole Analysis; the timeline is the per-video view."""

    a_clip(analysis, name="Tor von rechts aussen", category="Tore", half=0)
    a_clip(analysis, name="Block Mitte", category="Abwehr", half=1)
    workspace.refresh()

    assert [row["title"] for row in clip_rows(workspace)] == [
        "Tor von rechts aussen",
        "Block Mitte",
    ]


def test_the_clips_are_grouped_under_a_row_for_each_category(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", category="Tore")
    a_clip(analysis, name="Block", category="Abwehr")
    workspace.refresh()

    assert [(row["kind"], row["title"]) for row in rows(workspace)] == [
        ("category", "Tore"),
        ("clip", "Tor"),
        ("category", "Abwehr"),
        ("clip", "Block"),
    ]


def test_the_categories_keep_the_order_the_analysis_gives_them(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    """The Analysis's own order, not the order the Clips were marked in."""

    a_clip(analysis, name="Block", category="Abwehr")
    a_clip(analysis, name="Tor", category="Tore")
    workspace.refresh()

    assert [row["title"] for row in rows(workspace) if row["kind"] == "category"] == [
        "Tore",
        "Abwehr",
    ]


def test_a_category_with_no_clips_has_no_row_of_its_own(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", category="Tore")
    workspace.refresh()

    assert [row["title"] for row in rows(workspace) if row["kind"] == "category"] == [
        "Tore"
    ]


def test_clips_with_no_category_fall_to_the_end_under_their_own_heading(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Noch unsortiert")
    a_clip(analysis, name="Tor", category="Tore")
    workspace.refresh()

    assert [(row["kind"], row["title"]) for row in rows(workspace)] == [
        ("category", "Tore"),
        ("clip", "Tor"),
        ("category", UNCATEGORIZED_LABEL),
        ("clip", "Noch unsortiert"),
    ]


def test_a_category_named_like_the_uncategorized_heading_stays_a_separate_group(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    analysis.add_category(UNCATEGORIZED_LABEL, color="#3E9BC4")
    a_clip(analysis, name="Bewusst einsortiert", category=UNCATEGORIZED_LABEL)
    a_clip(analysis, name="Noch unsortiert")
    workspace.refresh()

    assert [(row["kind"], row["title"]) for row in rows(workspace)] == [
        ("category", UNCATEGORIZED_LABEL),
        ("clip", "Bewusst einsortiert"),
        ("category", UNCATEGORIZED_LABEL),
        ("clip", "Noch unsortiert"),
    ]


def test_within_a_category_clips_read_in_source_video_then_time_order(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    """A coach reads the Analysis as the match happened, half by half."""

    a_clip(analysis, name="Zweite Halbzeit, frueh", start_ms=5_000, half=1, category="Tore")
    a_clip(analysis, name="Erste Halbzeit, spaet", start_ms=900_000, half=0, category="Tore")
    a_clip(analysis, name="Erste Halbzeit, frueh", start_ms=60_000, half=0, category="Tore")
    workspace.refresh()

    assert [row["title"] for row in clip_rows(workspace)] == [
        "Erste Halbzeit, frueh",
        "Erste Halbzeit, spaet",
        "Zweite Halbzeit, frueh",
    ]


def test_a_category_row_counts_the_clips_under_it_and_carries_its_colour(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Erstes Tor", category="Tore")
    a_clip(analysis, name="Zweites Tor", category="Tore", start_ms=100_000)
    workspace.refresh()

    header = rows(workspace)[0]
    assert header["count"] == 2
    assert header["categoryColor"] == "#E2564A"


def test_an_uncategorized_group_carries_no_colour_of_its_own(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    """A grey invented here would be a colour outside `Theme.qml`."""

    a_clip(analysis, name="Noch unsortiert")
    workspace.refresh()

    assert rows(workspace)[0]["categoryColor"] == ""


# --- What one Clip row says -------------------------------------------------


def test_a_clip_row_carries_its_start_and_its_length_as_timecode(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", start_ms=843_000, end_ms=861_000)
    workspace.refresh()

    row = clip_rows(workspace)[0]
    assert row["startText"] == timecode.clock(843_000) == "00:14:03"
    assert row["durationText"] == timecode.duration(18_000) == "0:18"


def test_a_clip_row_names_the_clip_and_its_category_colour(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor von rechts aussen", category="Tore")
    workspace.refresh()

    row = clip_rows(workspace)[0]
    assert row["title"] == "Tor von rechts aussen"
    assert row["categoryColor"] == "#E2564A"


# --- The Source-video cue ---------------------------------------------------


def test_a_clip_row_in_a_one_video_analysis_carries_no_source_cue(
    player: FakePlayback, scheduler: Scheduler
) -> None:
    """Nothing to tell apart, so nothing is spent telling them apart."""

    analysis = Analysis("Spiel gegen Kiel")
    analysis.add_source_video("halbzeit-1.mp4", FIRST_HALF, duration_ms=FIRST_HALF_MS)
    a_clip(analysis, name="Tor")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), player, schedule=scheduler
    )
    scheduler.elapse()

    row = clip_rows(workspace)[0]
    assert row["sourceBadge"] == ""
    assert row["sourceCue"] == ""


def test_a_clip_row_in_a_multi_video_analysis_is_badged_with_its_half(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", half=0)
    a_clip(analysis, name="Block", half=1)
    workspace.refresh()

    assert [row["sourceBadge"] for row in clip_rows(workspace)] == ["H1", "H2"]


def test_the_badge_keeps_the_full_source_video_name_one_hover_away(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", half=1)
    workspace.refresh()

    assert clip_rows(workspace)[0]["sourceCue"] == "halbzeit-2.mp4"


def test_a_badge_is_the_leading_letter_and_the_trailing_number() -> None:
    assert source_badges(["halbzeit-1.mp4", "halbzeit-2.mp4"]) == ["H1", "H2"]
    assert source_badges(["2. Halbzeit.mp4"]) == ["H2"]
    assert source_badges(["Spielaufzeichnung.mp4"]) == ["S"]


def test_a_badge_ignores_a_date_in_front_of_the_name() -> None:
    """`2024-03-09 Kiel.mp4` is one video, not the ninth of anything."""

    assert source_badges(["2024-03-09 Kiel Halbzeit 1.mkv"]) == ["K1"]


def test_two_source_videos_never_get_the_same_badge(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    """A cue that cannot tell two videos apart is not a cue.

    The prototype's badge was a function of one name at a time, so an Analysis
    of `Angriff.mp4` and `Abwehr.mp4` badged both of them `A`.
    """

    assert source_badges(["Angriff.mp4", "Abwehr.mp4"]) == ["V1", "V2"]
    assert source_badges(["Halbzeit 1.mp4", "Halbzeit 1 (Kopie).mp4"]) == ["V1", "V2"]


def test_a_source_video_with_nothing_to_shorten_still_gets_a_badge() -> None:
    assert source_badges(["1.mp4", "2.mp4"]) == ["V1", "V2"]


# --- Navigating by Clip -----------------------------------------------------


def test_selecting_a_clip_seeks_the_player_to_its_start(
    workspace: WorkspaceViewModel, analysis: Analysis, player: FakePlayback
) -> None:
    clip = a_clip(analysis, name="Tor", start_ms=843_000, end_ms=861_000)
    workspace.refresh()

    workspace.navigateToClip(str(clip.id))

    assert player.position() == 843_000
    assert workspace.positionMs == 843_000


def test_selecting_a_clip_of_another_source_video_activates_that_video(
    workspace: WorkspaceViewModel,
    analysis: Analysis,
    player: FakePlayback,
    scheduler: Scheduler,
) -> None:
    """One action, not two: a coach clicks the Clip, not the video first."""

    clip = a_clip(analysis, name="Block Mitte", start_ms=120_000, half=1)
    workspace.refresh()

    workspace.navigateToClip(str(clip.id))
    assert scheduler.pending != [], "the new Source video was not primed"
    scheduler.elapse()

    assert player.location() == SECOND_HALF
    assert player.position() == 120_000
    assert workspace.durationMs == SECOND_HALF_MS


def test_selecting_a_clip_is_the_same_selection_the_timeline_draws(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    """One piece of state. Two would eventually disagree on screen."""

    clip = a_clip(analysis, name="Tor")
    workspace.refresh()

    workspace.navigateToClip(str(clip.id))

    assert workspace.selectedClipId == str(clip.id)
    assert [row["selected"] for row in clip_rows(workspace)] == [True]
    assert [row["selected"] for row in workspace.rangeModel.rows()] == [True]


def test_a_clip_selected_on_the_timeline_is_marked_in_the_list_too(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Erster", start_ms=10_000, end_ms=20_000)
    clip = a_clip(analysis, name="Zweiter", start_ms=30_000, end_ms=40_000)
    workspace.refresh()

    workspace.selectClip(str(clip.id))

    assert [row["selected"] for row in clip_rows(workspace)] == [False, True]


def test_selecting_a_clip_that_is_not_in_the_analysis_does_nothing(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.navigateToClip("not-a-clip")

    assert workspace.selectedClipId == ""
    assert player.location() == FIRST_HALF


def test_navigating_within_the_active_source_video_does_not_reload_it(
    workspace: WorkspaceViewModel,
    analysis: Analysis,
    player: FakePlayback,
    scheduler: Scheduler,
) -> None:
    """Reloading would take the picture black and prime it all over again."""

    clip = a_clip(analysis, name="Tor", start_ms=843_000)
    workspace.refresh()

    workspace.navigateToClip(str(clip.id))

    assert player.location() == FIRST_HALF
    assert scheduler.pending == [], "the Source video was loaded and primed again"


# --- The Videos tab ---------------------------------------------------------


def test_the_videos_tab_lists_every_source_video_with_the_active_one_marked(
    workspace: WorkspaceViewModel,
) -> None:
    assert [(row["name"], row["active"]) for row in videos(workspace)] == [
        ("halbzeit-1.mp4", True),
        ("halbzeit-2.mp4", False),
    ]


def test_a_source_video_with_no_clips_says_so_in_the_plural(
    workspace: WorkspaceViewModel,
) -> None:
    assert videos(workspace)[0]["clipCountText"] == "0 Clips"


def test_a_source_video_row_carries_its_length_and_how_many_clips_it_holds(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", half=0)
    a_clip(analysis, name="Block", half=1)
    a_clip(analysis, name="Zweiter Block", half=1, start_ms=200_000)
    workspace.refresh()

    assert [
        (row["durationText"], row["clipCountText"]) for row in videos(workspace)
    ] == [
        (timecode.clock(FIRST_HALF_MS), "1 Clip"),
        (timecode.clock(SECOND_HALF_MS), "2 Clips"),
    ]


def test_a_source_video_of_unknown_length_says_so_rather_than_guessing(
    player: FakePlayback, scheduler: Scheduler
) -> None:
    analysis = Analysis("Spiel gegen Kiel")
    analysis.add_source_video("halbzeit-1.mp4", FIRST_HALF)
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), player, schedule=scheduler
    )
    scheduler.elapse()

    assert videos(workspace)[0]["durationText"] == "--:--:--"


def test_the_videos_tab_marks_source_videos_that_do_not_resolve_as_unavailable(
    workspace: WorkspaceViewModel,
) -> None:
    """Neither fixture video exists on disk, so both are unavailable.

    The rest of the Analysis stays usable regardless: this only asserts the
    display state the Videos tab reads, not that anything else broke.
    """

    assert [row["available"] for row in videos(workspace)] == [False, False]


def test_a_source_video_present_on_disk_is_marked_available(
    tmp_path, player: FakePlayback, scheduler: Scheduler
) -> None:
    present_path = tmp_path / "halbzeit-1.mp4"
    present_path.write_bytes(b"video")
    analysis = Analysis("Spiel gegen Kiel")
    analysis.add_source_video("halbzeit-1.mp4", str(present_path))
    analysis.add_source_video("halbzeit-2.mp4", FIRST_HALF)
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), player, schedule=scheduler
    )
    scheduler.elapse()

    assert [row["available"] for row in videos(workspace)] == [True, False]


def test_relinking_an_unavailable_source_video_marks_it_available_and_reloads_it(
    tmp_path, player: FakePlayback, scheduler: Scheduler
) -> None:
    analysis = Analysis("Spiel gegen Kiel")
    missing_video = analysis.add_source_video("halbzeit-1.mp4", FIRST_HALF)
    document = AnalysisDocument(analysis)
    workspace = WorkspaceViewModel(document, player, schedule=scheduler)
    scheduler.elapse()

    replacement_path = tmp_path / "recovered.mp4"
    replacement_path.write_bytes(b"video")

    def _fake_relink(source_video_id, on_done) -> None:  # type: ignore[no-untyped-def]
        relinked = document.analysis.relink_source_video(
            source_video_id,
            str(replacement_path),
            duration_ms=1_000,
            byte_size=1,
            fingerprint="fake",
        )
        on_done(relinked is not None)

    workspace._workflow.relink_source_video = _fake_relink  # type: ignore[method-assign]

    relinked = _result(
        lambda on_done: workspace.relinkSourceVideo(str(missing_video.id), on_done)
    )
    scheduler.elapse()

    assert relinked is True
    assert videos(workspace)[0]["available"] is True
    assert player.location() == str(replacement_path)


def test_a_failed_relink_leaves_the_source_video_unavailable(
    workspace: WorkspaceViewModel,
) -> None:
    missing = videos(workspace)[0]["sourceId"]
    workspace._workflow.relink_source_video = (  # type: ignore[method-assign]
        lambda source_video_id, on_done: on_done(False)
    )

    result = _result(lambda on_done: workspace.relinkSourceVideo(missing, on_done))
    assert result is False
    assert videos(workspace)[0]["available"] is False


def test_relinking_an_unknown_source_video_id_does_nothing(
    workspace: WorkspaceViewModel,
) -> None:
    result = _result(
        lambda on_done: workspace.relinkSourceVideo("not-a-uuid", on_done)
    )
    assert result is False


def test_choosing_a_source_video_makes_it_the_one_the_player_shows(
    workspace: WorkspaceViewModel, player: FakePlayback, scheduler: Scheduler
) -> None:
    second = videos(workspace)[1]["sourceId"]

    workspace.selectSourceVideo(second)
    scheduler.elapse()

    assert player.location() == SECOND_HALF
    assert [row["active"] for row in videos(workspace)] == [False, True]


def test_choosing_a_source_video_leaves_no_clip_of_the_old_one_selected(
    workspace: WorkspaceViewModel, analysis: Analysis, scheduler: Scheduler
) -> None:
    """The timeline is the new video's; a selection on the old one is stale."""

    clip = a_clip(analysis, name="Tor", half=0)
    workspace.refresh()
    workspace.navigateToClip(str(clip.id))

    workspace.selectSourceVideo(videos(workspace)[1]["sourceId"])
    scheduler.elapse()

    assert workspace.selectedClipId == ""


def test_choosing_the_source_video_already_playing_changes_nothing(
    workspace: WorkspaceViewModel, analysis: Analysis, scheduler: Scheduler
) -> None:
    clip = a_clip(analysis, name="Tor", half=0)
    workspace.refresh()
    workspace.navigateToClip(str(clip.id))

    workspace.selectSourceVideo(videos(workspace)[0]["sourceId"])
    scheduler.elapse()

    assert workspace.selectedClipId == str(clip.id)


def test_choosing_a_source_video_that_is_not_in_the_analysis_does_nothing(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.selectSourceVideo("not-a-video")

    assert player.location() == FIRST_HALF


# --- Renaming, reordering and removing Source videos ------------------------


def test_renaming_a_source_video_updates_the_videos_tab(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    first_id = str(analysis.source_videos[0].id)

    assert workspace.renameSourceVideo(first_id, "Halbzeit 1") is True

    assert [row["name"] for row in videos(workspace)] == [
        "Halbzeit 1",
        "halbzeit-2.mp4",
    ]


def test_reordering_source_videos_reorders_the_videos_tab(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    first_id, second_id = (str(source.id) for source in analysis.source_videos)

    assert workspace.reorderSourceVideos([second_id, first_id]) is True

    assert [row["sourceId"] for row in videos(workspace)] == [second_id, first_id]


def test_moving_a_source_video_later_swaps_it_with_its_neighbour(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    first_id, second_id = (str(source.id) for source in analysis.source_videos)

    assert workspace.moveSourceVideoLater(first_id) is True

    assert [row["sourceId"] for row in videos(workspace)] == [second_id, first_id]


def test_moving_the_last_source_video_later_does_nothing(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    second_id = str(analysis.source_videos[1].id)

    assert workspace.moveSourceVideoLater(second_id) is False

    assert [row["sourceId"] for row in videos(workspace)] == [
        str(analysis.source_videos[0].id),
        second_id,
    ]


def test_moving_the_first_source_video_earlier_does_nothing(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    first_id = str(analysis.source_videos[0].id)

    assert workspace.moveSourceVideoEarlier(first_id) is False


def test_clip_count_for_a_source_video_is_what_removing_it_would_take(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    a_clip(analysis, name="Tor", half=0)
    a_clip(analysis, name="7m", half=0)
    workspace.refresh()
    first_id = str(analysis.source_videos[0].id)
    second_id = str(analysis.source_videos[1].id)

    assert workspace.clipCountForSourceVideo(first_id) == 2
    assert workspace.clipCountForSourceVideo(second_id) == 0


def test_removing_a_source_video_without_clips_leaves_the_other_active(
    workspace: WorkspaceViewModel, analysis: Analysis, player: FakePlayback
) -> None:
    second_id = str(analysis.source_videos[1].id)

    assert workspace.removeSourceVideo(second_id) is True

    assert len(videos(workspace)) == 1
    assert player.location() == FIRST_HALF
    assert workspace.hasVideo is True


def test_removing_the_active_source_video_takes_its_clips_and_switches_video(
    workspace: WorkspaceViewModel,
    analysis: Analysis,
    player: FakePlayback,
    scheduler: Scheduler,
) -> None:
    clip = a_clip(analysis, name="Tor", half=0)
    workspace.refresh()
    workspace.navigateToClip(str(clip.id))
    first_id = str(analysis.source_videos[0].id)

    assert workspace.removeSourceVideo(first_id) is True
    scheduler.elapse()

    assert [row["sourceId"] for row in videos(workspace)] == [
        str(analysis.source_videos[0].id)
    ]
    assert player.location() == SECOND_HALF
    assert workspace.selectedClipId == ""
    assert clip_rows(workspace) == []


def test_removing_the_last_source_video_leaves_no_stale_player_or_selection(
    document: AnalysisDocument,
    analysis: Analysis,
    player: FakePlayback,
    scheduler: Scheduler,
) -> None:
    # Trim to one Source video first, so removing it removes the last one.
    second_id = analysis.source_videos[1].id
    analysis.remove_source_video(second_id)
    workspace = WorkspaceViewModel(document, player, schedule=scheduler)
    scheduler.elapse()
    first_id = str(analysis.source_videos[0].id)

    assert workspace.removeSourceVideo(first_id) is True
    scheduler.elapse()

    assert videos(workspace) == ()
    assert workspace.hasVideo is False
    assert player.is_loaded() is False
    assert analysis.source_videos == ()


# --- Which tab is showing ---------------------------------------------------


def test_the_sidebar_opens_on_the_clips(workspace: WorkspaceViewModel) -> None:
    assert workspace.sidebarTab == "clips"


def test_the_analyst_can_switch_to_the_videos_and_back(
    workspace: WorkspaceViewModel,
) -> None:
    changed: list[str] = []
    workspace.sidebarTabChanged.connect(lambda: changed.append(workspace.sidebarTab))

    workspace.setSidebarTab("videos")
    workspace.setSidebarTab("videos")
    workspace.setSidebarTab("clips")

    assert changed == ["videos", "clips"]


def test_a_tab_the_sidebar_does_not_have_is_ignored(
    workspace: WorkspaceViewModel,
) -> None:
    workspace.setSidebarTab("kategorien")

    assert workspace.sidebarTab == "clips"


def test_which_tab_is_showing_never_reaches_the_analysis_file(
    workspace: WorkspaceViewModel, document: AnalysisDocument, tmp_path
) -> None:
    """A view is not analysis. Saving one would make opening it a surprise."""

    workspace.setSidebarTab("videos")

    assert document.dirty is False

    saved = document.save_as(tmp_path / "spiel.analysis").read_text(encoding="utf-8")
    assert "sidebar" not in saved
    assert "tab" not in saved


def test_nothing_the_sidebar_does_dirties_the_analysis(
    workspace: WorkspaceViewModel, analysis: Analysis, document: AnalysisDocument
) -> None:
    clip = a_clip(analysis, name="Tor")
    workspace.refresh()
    dirty_after_marking = document.dirty

    workspace.navigateToClip(str(clip.id))
    workspace.selectSourceVideo(videos(workspace)[1]["sourceId"])
    workspace.setSidebarTab("videos")

    assert document.dirty == dirty_after_marking


# --- The lists follow the Analysis ------------------------------------------


def test_a_clip_added_to_the_analysis_appears_in_the_list(
    workspace: WorkspaceViewModel, analysis: Analysis
) -> None:
    assert clip_rows(workspace) == []

    a_clip(analysis, name="Tor")
    workspace.refresh()

    assert [row["title"] for row in clip_rows(workspace)] == ["Tor"]


def test_opening_another_analysis_empties_the_lists_of_the_old_one(
    workspace: WorkspaceViewModel,
    analysis: Analysis,
    document: AnalysisDocument,
    scheduler: Scheduler,
    tmp_path,
) -> None:
    a_clip(analysis, name="Tor")
    workspace.refresh()
    document.save_as(tmp_path / "spiel.analysis")

    assert _result(workspace.newAnalysis) is True
    scheduler.elapse()

    assert clip_rows(workspace) == []
    assert videos(workspace) == ()
