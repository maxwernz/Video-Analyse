"""Planning a Combined export: grouping, ordering, rearranging, preflight.

These tests exercise `export_planning` entirely against in-memory `Analysis`
and `AnalysisDocument` state, with no encoder involved -- the planning half
of the split `export_planning.py`'s module docstring describes. The small
cross-video render itself is covered separately, with real media, in
`tests/test_video_export.py`.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from analysis import Analysis, AnalysisDocument
from export_planning import (
    ExportUnavailableError,
    UNCATEGORIZED_LABEL,
    build_export_list,
    preflight_export,
    reorder_export_list,
)


def _analysis_with_two_videos_and_categories() -> tuple[Analysis, dict]:
    """A small Analysis: two Source videos and two Categories, out of order.

    The Category order is deliberately Tor-then-Abwehr, and the Source-video
    order deliberately second-half-then-first-half, so a test that only
    passes by accident of insertion order (rather than by reading the
    Analysis's actual order) will fail.
    """

    analysis = Analysis("Match")
    tor = analysis.add_category("Tor")
    abwehr = analysis.add_category("Abwehr")
    second_half = analysis.add_source_video("second-half.mp4", "/videos/second-half.mp4")
    first_half = analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    return analysis, {
        "tor": tor,
        "abwehr": abwehr,
        "second_half": second_half,
        "first_half": first_half,
    }


# --- Grouping and ordering ---------------------------------------------------


def test_export_list_groups_by_analysis_defined_category_order() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    abwehr_clip = analysis.add_clip(
        ids["first_half"].id, "Abwehr clip", 1_000, 2_000, category_id=ids["abwehr"].id
    )
    tor_clip = analysis.add_clip(
        ids["first_half"].id, "Tor clip", 3_000, 4_000, category_id=ids["tor"].id
    )

    # Selected in Abwehr-then-Tor order; the Analysis's own Category order
    # is Tor-then-Abwehr, and that is what must win.
    entries = build_export_list(analysis, [abwehr_clip.id, tor_clip.id])

    assert [entry.clip_id for entry in entries] == [tor_clip.id, abwehr_clip.id]


def test_export_list_orders_within_a_category_by_source_video_then_start_time() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    # Source-video order is second-half, then first-half.
    later_in_first_half = analysis.add_clip(
        ids["first_half"].id, "Later", 5_000, 6_000, category_id=ids["tor"].id
    )
    earlier_in_first_half = analysis.add_clip(
        ids["first_half"].id, "Earlier", 1_000, 2_000, category_id=ids["tor"].id
    )
    in_second_half = analysis.add_clip(
        ids["second_half"].id, "Second half", 500, 1_500, category_id=ids["tor"].id
    )

    entries = build_export_list(
        analysis,
        [later_in_first_half.id, in_second_half.id, earlier_in_first_half.id],
    )

    assert [entry.clip_id for entry in entries] == [
        in_second_half.id,
        earlier_in_first_half.id,
        later_in_first_half.id,
    ]


def test_uncategorized_clips_form_a_final_group() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    categorized = analysis.add_clip(
        ids["first_half"].id, "Filed", 1_000, 2_000, category_id=ids["abwehr"].id
    )
    uncategorized = analysis.add_clip(
        ids["first_half"].id, "Unfiled", 100, 200, category_id=None
    )

    entries = build_export_list(analysis, [uncategorized.id, categorized.id])

    assert [entry.clip_id for entry in entries] == [categorized.id, uncategorized.id]
    assert entries[-1].category_name == UNCATEGORIZED_LABEL
    assert entries[-1].category_id is None


def test_build_export_list_drops_unknown_and_duplicate_clip_ids() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    clip = analysis.add_clip(ids["first_half"].id, "Clip", 1_000, 2_000)

    entries = build_export_list(analysis, [clip.id, uuid4(), clip.id])

    assert [entry.clip_id for entry in entries] == [clip.id]


def test_building_an_export_list_never_mutates_the_analysis() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    clip = analysis.add_clip(ids["first_half"].id, "Clip", 1_000, 2_000)
    revision = analysis.revision

    build_export_list(analysis, [clip.id])

    assert analysis.revision == revision
    assert analysis.clips == (clip,)


# --- Rearranging --------------------------------------------------------------


def test_rearranging_the_export_list_is_independent_of_analysis_order() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    first = analysis.add_clip(ids["first_half"].id, "First", 1_000, 2_000)
    second = analysis.add_clip(ids["first_half"].id, "Second", 3_000, 4_000)
    entries = build_export_list(analysis, [first.id, second.id])
    revision = analysis.revision

    rearranged = reorder_export_list(entries, [second.id, first.id])

    assert [entry.clip_id for entry in rearranged] == [second.id, first.id]
    # Nothing about Clip creation order, in the Analysis, moved.
    assert [clip.id for clip in analysis.clips] == [first.id, second.id]
    assert analysis.revision == revision


def test_reordering_with_a_missing_or_extra_entry_is_refused() -> None:
    analysis, ids = _analysis_with_two_videos_and_categories()
    first = analysis.add_clip(ids["first_half"].id, "First", 1_000, 2_000)
    second = analysis.add_clip(ids["first_half"].id, "Second", 3_000, 4_000)
    entries = build_export_list(analysis, [first.id, second.id])

    with pytest.raises(ValueError):
        reorder_export_list(entries, [first.id])

    with pytest.raises(ValueError):
        reorder_export_list(entries, [first.id, second.id, uuid4()])


# --- Building and rearranging never arms Recovery ----------------------------


def test_building_and_rearranging_an_export_list_never_arms_recovery(
    tmp_path: Path,
) -> None:
    """The transience #19's Recovery scheduling depends on.

    `ApplicationWorkflow.note_recovery_activity` only schedules a snapshot
    when `Analysis.revision` has moved since it last looked; if planning an
    Export list moved nothing, offering it to `note_recovery_activity`
    schedules nothing either -- exactly the guarantee `tests/
    test_application_workflow.py` already asserts for view-only activity.
    """

    from analysis import RecoverySnapshotStore, new_analysis_document
    from application_workflow import ApplicationWorkflow

    class _RefusingPresenter:
        def ask_unsaved_changes(self):  # pragma: no cover - not exercised
            raise AssertionError

        def choose_analysis_to_open(self):
            return None

        def choose_analysis_destination(self, suggested_name: str):
            return None

        def choose_source_video(self):
            return None

        def choose_replacement_media(self, display_name: str):
            return None

        def confirm_source_video_replacement(self, display_name: str) -> bool:
            return False

        def report_failure(self, title: str, message: str) -> None:
            return None

        def ask_external_change_conflict(self):
            raise AssertionError  # pragma: no cover - not exercised

        def offer_recovered_analysis(self) -> bool:
            return False

    class _RecordingScheduler:
        def __init__(self) -> None:
            self.scheduled = 0

        def schedule(self, run) -> None:
            self.scheduled += 1

        def cancel(self) -> None:
            return None

    scheduler = _RecordingScheduler()
    document = new_analysis_document("Match")
    workflow = ApplicationWorkflow(
        _RefusingPresenter(),
        document=document,
        recovery_store=RecoverySnapshotStore(tmp_path / "recovery-store"),
        recovery_scheduler=scheduler,
    )
    analysis = workflow.analysis
    source = analysis.add_source_video("half.mp4", "/videos/half.mp4")
    clip_a = analysis.add_clip(source.id, "A", 1_000, 2_000)
    clip_b = analysis.add_clip(source.id, "B", 3_000, 4_000)
    # Reset the workflow's revision baseline past the setup above, as
    # `note_recovery_activity` would already have been offered those real
    # Analysis changes by the interface that made them.
    workflow.note_recovery_activity()
    scheduler.scheduled = 0

    entries = build_export_list(analysis, [clip_a.id, clip_b.id])
    reorder_export_list(entries, [clip_b.id, clip_a.id])
    workflow.note_recovery_activity()

    assert scheduler.scheduled == 0


# --- Source resolution and preflight -----------------------------------------


def test_preflight_resolves_through_stable_source_video_identity(
    tmp_path: Path,
) -> None:
    """Preflight must use `AnalysisDocument.resolve_source_video`, not a path.

    The Source video's *recorded* location is stale (moved away); its real
    media now sits only at the location relative to the Analysis file --
    exactly the "moved together" case `AnalysisDocument.resolve_source_video`
    exists for. A preflight that instead checked the recorded location
    directly, or checked whatever happens to be the Active Source video's
    player path, would report this available media as missing.
    """

    analysis_path = tmp_path / "match.analysis"
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    video_path = videos_dir / "first-half.mp4"
    video_path.write_bytes(b"not a real video, just needs to exist")

    analysis = Analysis("Match")
    source = analysis.add_source_video(
        "first-half.mp4",
        "/no/longer/here/first-half.mp4",
        relative_path="videos/first-half.mp4",
    )
    clip = analysis.add_clip(source.id, "Clip", 100, 200)
    document = AnalysisDocument(analysis)
    document.save_as(analysis_path)

    entries = build_export_list(analysis, [clip.id])
    preflight = preflight_export(document, entries)

    assert preflight.ready
    assert preflight.resolved_paths[source.id] == video_path


def test_preflight_reports_the_complete_unavailable_set_not_the_first() -> None:
    analysis = Analysis("Match")
    missing_a = analysis.add_source_video("a.mp4", "/does/not/exist/a.mp4")
    missing_b = analysis.add_source_video("b.mp4", "/does/not/exist/b.mp4")
    clip_a = analysis.add_clip(missing_a.id, "A", 100, 200)
    clip_b = analysis.add_clip(missing_b.id, "B", 100, 200)
    document = AnalysisDocument(analysis)

    entries = build_export_list(analysis, [clip_a.id, clip_b.id])
    preflight = preflight_export(document, entries)

    assert not preflight.ready
    assert {unavailable.source_video_id for unavailable in preflight.unavailable} == {
        missing_a.id,
        missing_b.id,
    }
    assert {unavailable.display_name for unavailable in preflight.unavailable} == {
        "a.mp4",
        "b.mp4",
    }


def test_preflight_reports_a_source_video_removed_after_the_list_was_built() -> None:
    """The Export list can outlive an Analysis edit; preflight must not crash.

    An analyst can remove a Source video (and its Clips) from the Analysis
    while an already-built Export list still names one of its Clips.
    Preflight reports that as unavailable media, the same as missing files,
    rather than raising `UnknownEntityError` out of the one pass meant to
    find everything that needs relinking.
    """

    analysis = Analysis("Match")
    source = analysis.add_source_video("a.mp4", "/does/not/exist/a.mp4")
    clip = analysis.add_clip(source.id, "A", 100, 200)
    document = AnalysisDocument(analysis)
    entries = build_export_list(analysis, [clip.id])

    analysis.remove_source_video(source.id)

    preflight = preflight_export(document, entries)

    assert not preflight.ready
    assert preflight.unavailable[0].source_video_id == source.id


def test_preflighting_never_mutates_the_analysis_or_document() -> None:
    analysis = Analysis("Match")
    source = analysis.add_source_video("a.mp4", "/does/not/exist/a.mp4")
    clip = analysis.add_clip(source.id, "A", 100, 200)
    document = AnalysisDocument(analysis)
    revision = analysis.revision

    entries = build_export_list(analysis, [clip.id])
    preflight_export(document, entries)

    assert analysis.revision == revision
    assert not document.dirty


def test_render_combined_export_refuses_when_media_is_unavailable(
    tmp_path: Path,
) -> None:
    from export_planning import render_combined_export

    analysis = Analysis("Match")
    source = analysis.add_source_video("a.mp4", "/does/not/exist/a.mp4")
    clip = analysis.add_clip(source.id, "A", 100, 200)
    document = AnalysisDocument(analysis)
    entries = build_export_list(analysis, [clip.id])

    with pytest.raises(ExportUnavailableError) as excinfo:
        render_combined_export(document, entries, str(tmp_path / "export.mp4"))

    assert excinfo.value.unavailable[0].source_video_id == source.id
    # No render began: nothing was written.
    assert not (tmp_path / "export.mp4").exists()
