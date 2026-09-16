from __future__ import annotations

from uuid import uuid4

import pytest

from analysis import (
    Analysis,
    AnalysisDocument,
    InvalidAnalysisDataError,
    UnknownEntityError,
    apply_category_template,
    new_analysis_document,
)


def _analysis_with_source() -> Analysis:
    analysis = Analysis("Match")
    analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    return analysis


def test_new_analysis_is_empty_and_has_stable_identity() -> None:
    analysis = Analysis("")

    assert analysis.title == ""
    assert analysis.source_videos == ()
    assert analysis.categories == ()
    assert analysis.clips == ()
    assert analysis.id == analysis.id


def test_title_is_editable_and_advances_the_revision() -> None:
    analysis = Analysis("")
    revision = analysis.revision

    analysis.set_title("Season opener")

    assert analysis.title == "Season opener"
    assert analysis.revision > revision


def test_setting_the_same_title_does_not_advance_the_revision() -> None:
    analysis = Analysis("Season opener")
    revision = analysis.revision

    analysis.set_title("Season opener")

    assert analysis.revision == revision


def test_a_new_analysis_without_a_source_video_cannot_be_saved(tmp_path) -> None:
    from analysis import EmptyAnalysisError

    document = new_analysis_document("Empty")

    with pytest.raises(EmptyAnalysisError):
        document.save_as(tmp_path / "empty.analysis")


def test_new_analysis_document_starts_clean_with_the_default_categories() -> None:
    document = new_analysis_document("Empty")

    assert [category.name for category in document.analysis.categories] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]
    assert document.dirty is False


def test_applying_the_category_template_twice_keeps_one_set_of_categories() -> None:
    analysis = Analysis("Match")
    apply_category_template(analysis)
    apply_category_template(analysis)

    assert [category.name for category in analysis.categories] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]


def test_adding_the_first_source_video_advances_the_revision() -> None:
    analysis = Analysis("Match")
    revision = analysis.revision

    source_video = analysis.add_source_video("first-half.mp4", "/videos/a.mp4")

    assert analysis.source_videos == (source_video,)
    assert analysis.revision > revision


def test_clips_are_created_edited_and_removed_through_analysis_operations() -> None:
    analysis = _analysis_with_source()
    source_video = analysis.source_videos[0]
    category = analysis.add_category("Angriff", "#EF4444")

    clip = analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    assert clip.category_id is None

    revision = analysis.revision
    updated = analysis.update_clip(
        clip.id,
        name="Fast break finish",
        notes="Left wing",
        category_id=category.id,
    )

    assert updated.id == clip.id
    assert updated.name == "Fast break finish"
    assert updated.notes == "Left wing"
    assert updated.category_id == category.id
    assert updated.start_ms == 1_000
    assert analysis.clip(clip.id) == updated
    assert analysis.revision > revision

    revision = analysis.revision
    analysis.remove_clip(clip.id)

    assert analysis.clips == ()
    assert analysis.revision > revision


def test_updating_a_clip_with_unchanged_values_does_not_advance_the_revision() -> None:
    analysis = _analysis_with_source()
    clip = analysis.add_clip(analysis.source_videos[0].id, "Fast break", 1_000, 2_000)
    revision = analysis.revision

    analysis.update_clip(clip.id, name="Fast break")

    assert analysis.revision == revision


def test_clip_updates_enforce_the_interval_invariant() -> None:
    analysis = _analysis_with_source()
    clip = analysis.add_clip(analysis.source_videos[0].id, "Fast break", 1_000, 2_000)

    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_clip(clip.id, end_ms=1_000)
    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_clip(clip.id, name="  ")
    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_clip(clip.id, start_ms=-1)

    assert analysis.clip(clip.id) == clip


def test_rejected_boundaries_leave_the_analysis_untouched() -> None:
    """A rejected boundary change must not even advance the revision.

    The Analysis document reads the revision to decide it has unsaved work, so
    a boundary the model refuses would otherwise leave a dirty Analysis behind.
    """
    analysis = _analysis_with_source()
    clip = analysis.add_clip(analysis.source_videos[0].id, "Fast break", 1_000, 2_000)
    revision = analysis.revision

    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_clip(clip.id, start_ms=9_000, end_ms=4_000)

    assert analysis.clip(clip.id) == clip
    assert analysis.revision == revision


def test_clip_updates_reject_an_unknown_category() -> None:
    from uuid import uuid4

    analysis = _analysis_with_source()
    clip = analysis.add_clip(analysis.source_videos[0].id, "Fast break", 1_000, 2_000)

    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_clip(clip.id, category_id=uuid4())


def test_removing_a_clip_keeps_the_creation_order_contiguous() -> None:
    analysis = _analysis_with_source()
    source_video_id = analysis.source_videos[0].id
    first = analysis.add_clip(source_video_id, "First", 0, 1_000)
    analysis.add_clip(source_video_id, "Second", 1_000, 2_000)
    third = analysis.add_clip(source_video_id, "Third", 2_000, 3_000)

    analysis.remove_clip(first.id)

    assert [clip.creation_order for clip in analysis.clips] == [0, 1]
    assert [clip.name for clip in analysis.clips] == ["Second", "Third"]

    fourth = analysis.add_clip(source_video_id, "Fourth", 3_000, 4_000)
    assert fourth.creation_order == 2
    assert analysis.clip(third.id).creation_order == 1


def test_a_failed_transaction_leaves_neither_content_nor_revision_behind() -> None:
    analysis = _analysis_with_source()
    source_video_id = analysis.source_videos[0].id
    revision = analysis.revision

    with pytest.raises(InvalidAnalysisDataError):
        with analysis.transaction():
            analysis.add_category("Konter", "#F59E0B")
            analysis.add_clip(source_video_id, "  ", 1_000, 2_000)

    assert analysis.categories == ()
    assert analysis.clips == ()
    assert analysis.revision == revision


def test_a_successful_transaction_keeps_every_change() -> None:
    analysis = _analysis_with_source()
    source_video_id = analysis.source_videos[0].id

    with analysis.transaction():
        category = analysis.add_category("Konter", "#F59E0B")
        analysis.add_clip(
            source_video_id,
            "Fast break",
            1_000,
            2_000,
            category_id=category.id,
        )

    assert [existing.name for existing in analysis.categories] == ["Konter"]
    assert analysis.clips[0].category_id == category.id


def test_unknown_entities_are_reported_as_unknown() -> None:
    from uuid import uuid4

    analysis = _analysis_with_source()

    with pytest.raises(UnknownEntityError):
        analysis.clip(uuid4())
    with pytest.raises(UnknownEntityError):
        analysis.remove_clip(uuid4())
    with pytest.raises(UnknownEntityError):
        analysis.update_category(uuid4(), name="Angriff")
    with pytest.raises(UnknownEntityError):
        analysis.remove_source_video(uuid4())


def test_renaming_a_category_preserves_its_clips() -> None:
    analysis = _analysis_with_source()
    category = analysis.add_category("Angriff", "#EF4444")
    clip = analysis.add_clip(
        analysis.source_videos[0].id,
        "Fast break",
        1_000,
        2_000,
        category_id=category.id,
    )
    revision = analysis.revision

    renamed = analysis.update_category(category.id, name="Angriff rechts")

    assert renamed.id == category.id
    assert renamed.name == "Angriff rechts"
    assert analysis.clip(clip.id).category_id == category.id
    assert analysis.revision > revision


def test_reordering_categories_preserves_clip_relationships() -> None:
    analysis = _analysis_with_source()
    attack = analysis.add_category("Angriff", "#EF4444")
    defence = analysis.add_category("Abwehr", "#3B82F6")
    clip = analysis.add_clip(
        analysis.source_videos[0].id,
        "Fast break",
        1_000,
        2_000,
        category_id=attack.id,
    )

    analysis.reorder_categories([defence.id, attack.id])

    assert [category.id for category in analysis.categories] == [defence.id, attack.id]
    assert analysis.clip(clip.id).category_id == attack.id


def test_category_identity_and_order_survive_an_analysis_file_round_trip(tmp_path) -> None:
    document = AnalysisDocument(_analysis_with_source())
    analysis = document.analysis
    attack = analysis.add_category("Angriff", "#EF4444")
    defence = analysis.add_category("Abwehr", "#3B82F6")
    clip = analysis.add_clip(
        analysis.source_videos[0].id,
        "Fast break",
        1_000,
        2_000,
        category_id=attack.id,
    )
    analysis.reorder_categories([defence.id, attack.id])
    path = document.save_as(tmp_path / "match.analysis")

    reopened = AnalysisDocument.new()
    reopened.load(path)

    assert [category.id for category in reopened.analysis.categories] == [
        defence.id,
        attack.id,
    ]
    assert reopened.analysis.clip(clip.id).category_id == attack.id


def test_category_names_stay_unique_after_trimmed_case_insensitive_comparison() -> None:
    analysis = _analysis_with_source()
    analysis.add_category("Angriff", "#EF4444")
    defence = analysis.add_category("Abwehr", "#3B82F6")

    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_category(defence.id, name="  angriff ")

    assert analysis.category(defence.id).name == "Abwehr"


def test_a_category_may_be_renamed_to_a_different_spelling_of_itself() -> None:
    analysis = _analysis_with_source()
    category = analysis.add_category("Angriff", "#EF4444")

    renamed = analysis.update_category(category.id, name="ANGRIFF")

    assert renamed.name == "ANGRIFF"


def test_removing_a_category_leaves_its_clips_uncategorized() -> None:
    analysis = _analysis_with_source()
    category = analysis.add_category("Angriff", "#EF4444")
    clip = analysis.add_clip(
        analysis.source_videos[0].id,
        "Fast break",
        1_000,
        2_000,
        category_id=category.id,
    )

    analysis.remove_category(category.id)

    assert analysis.categories == ()
    assert analysis.clip(clip.id).category_id is None


def test_removing_a_source_video_removes_its_clips() -> None:
    analysis = _analysis_with_source()
    source_video = analysis.source_videos[0]
    analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)

    analysis.remove_source_video(source_video.id)

    assert analysis.source_videos == ()
    assert analysis.clips == ()


def test_renaming_a_source_video_preserves_its_clips() -> None:
    analysis = _analysis_with_source()
    source_video = analysis.source_videos[0]
    clip = analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)

    renamed = analysis.rename_source_video(source_video.id, "Halbzeit 1")

    assert renamed.id == source_video.id
    assert renamed.display_name == "Halbzeit 1"
    assert analysis.clip(clip.id).source_video_id == source_video.id


def test_reordering_source_videos_preserves_every_clip_relationship() -> None:
    analysis = Analysis("Match")
    first = analysis.add_source_video("first-half.mp4", "/videos/first.mp4")
    second = analysis.add_source_video("second-half.mp4", "/videos/second.mp4")
    first_clip = analysis.add_clip(first.id, "Fast break", 1_000, 2_000)
    second_clip = analysis.add_clip(second.id, "Turnover", 3_000, 4_000)
    revision = analysis.revision

    analysis.reorder_source_videos([second.id, first.id])

    assert [source.id for source in analysis.source_videos] == [second.id, first.id]
    assert analysis.clip(first_clip.id).source_video_id == first.id
    assert analysis.clip(second_clip.id).source_video_id == second.id
    assert analysis.revision > revision


def test_reordering_to_the_same_order_does_not_advance_the_revision() -> None:
    analysis = Analysis("Match")
    first = analysis.add_source_video("first-half.mp4", "/videos/first.mp4")
    second = analysis.add_source_video("second-half.mp4", "/videos/second.mp4")
    revision = analysis.revision

    analysis.reorder_source_videos([first.id, second.id])

    assert analysis.revision == revision


def test_reordering_rejects_anything_but_a_permutation_of_every_source_video() -> None:
    analysis = Analysis("Match")
    first = analysis.add_source_video("first-half.mp4", "/videos/first.mp4")
    analysis.add_source_video("second-half.mp4", "/videos/second.mp4")

    with pytest.raises(InvalidAnalysisDataError):
        analysis.reorder_source_videos([first.id])


def test_adding_media_matching_an_existing_source_video_by_location_is_a_duplicate() -> None:
    analysis = Analysis("Match")
    analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )

    with pytest.raises(InvalidAnalysisDataError):
        analysis.add_or_relink_source_video(
            "first-half.mp4",
            "/videos/first-half.mp4",
            duration_ms=2_700_000,
            byte_size=123,
            fingerprint="sampled-sha256:same",
        )


def test_adding_media_matching_an_existing_source_video_from_elsewhere_relinks_it() -> None:
    analysis = Analysis("Match")
    original = analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )
    clip = analysis.add_clip(original.id, "Fast break", 1_000, 2_000)

    relinked = analysis.add_or_relink_source_video(
        "first-half.mp4",
        "/moved/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )

    assert relinked.id == original.id
    assert relinked.location == "/moved/first-half.mp4"
    assert len(analysis.source_videos) == 1
    assert analysis.clip(clip.id).source_video_id == original.id


def test_media_that_only_partially_matches_never_relinks_and_never_duplicates() -> None:
    analysis = Analysis("Match")
    analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )

    second = analysis.add_or_relink_source_video(
        "second-half.mp4",
        "/videos/second-half.mp4",
        duration_ms=2_700_000,
        byte_size=456,
        fingerprint="sampled-sha256:different",
    )

    assert len(analysis.source_videos) == 2
    assert second.location == "/videos/second-half.mp4"


def test_relinking_a_source_video_points_its_identity_at_new_media_and_keeps_clips() -> None:
    analysis = Analysis("Match")
    original = analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )
    clip = analysis.add_clip(original.id, "Fast break", 1_000, 2_000)
    revision = analysis.revision

    relinked = analysis.relink_source_video(
        original.id,
        "/recovered/first-half.mp4",
        relative_path="first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )

    assert relinked.id == original.id
    assert relinked.location == "/recovered/first-half.mp4"
    assert relinked.relative_path == "first-half.mp4"
    assert analysis.revision == revision + 1
    assert len(analysis.source_videos) == 1
    assert analysis.clip(clip.id).source_video_id == original.id
    assert analysis.clip(clip.id).start_ms == 1_000


def test_relinking_only_a_location_preserves_previously_recorded_signals() -> None:
    """`UNCHANGED` is the default so a partial relink cannot wipe out data.

    A caller — an automatic "moved together" resolution persisting what it
    found, say — that relinks only `location` must not erase a duration,
    byte size, or fingerprint this identity already carried.
    """

    analysis = Analysis("Match")
    original = analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )

    relinked = analysis.relink_source_video(original.id, "/recovered/first-half.mp4")

    assert relinked.location == "/recovered/first-half.mp4"
    assert relinked.duration_ms == 2_700_000
    assert relinked.byte_size == 123
    assert relinked.fingerprint == "sampled-sha256:same"


def test_relinking_can_adopt_a_mismatched_fingerprint_when_the_caller_allows_it() -> None:
    """Verification belongs to `ApplicationWorkflow`; the model only records."""

    analysis = Analysis("Match")
    original = analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123,
        fingerprint="sampled-sha256:same",
    )

    relinked = analysis.relink_source_video(
        original.id,
        "/videos/different-recording.mp4",
        duration_ms=1_000,
        byte_size=999,
        fingerprint="sampled-sha256:different",
    )

    assert relinked.fingerprint == "sampled-sha256:different"
    assert relinked.duration_ms == 1_000
    assert relinked.byte_size == 999


def test_relinking_rejects_a_location_already_used_by_another_source_video() -> None:
    analysis = Analysis("Match")
    first = analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    analysis.add_source_video("second-half.mp4", "/videos/second-half.mp4")

    with pytest.raises(InvalidAnalysisDataError):
        analysis.relink_source_video(first.id, "/videos/second-half.mp4")


def test_relinking_rejects_a_fingerprint_already_used_by_another_source_video() -> None:
    analysis = Analysis("Match")
    first = analysis.add_source_video(
        "first-half.mp4", "/videos/first-half.mp4", fingerprint="sampled-sha256:a"
    )
    analysis.add_source_video(
        "second-half.mp4", "/videos/second-half.mp4", fingerprint="sampled-sha256:b"
    )

    with pytest.raises(InvalidAnalysisDataError):
        analysis.relink_source_video(
            first.id, "/videos/relinked.mp4", fingerprint="sampled-sha256:b"
        )


def test_relinking_an_unknown_source_video_is_reported_as_unknown() -> None:
    analysis = Analysis("Match")

    with pytest.raises(UnknownEntityError):
        analysis.relink_source_video(uuid4(), "/videos/anything.mp4")


def test_a_failed_relink_leaves_the_analysis_untouched() -> None:
    analysis = Analysis("Match")
    first = analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    analysis.add_source_video("second-half.mp4", "/videos/second-half.mp4")
    revision = analysis.revision

    with pytest.raises(InvalidAnalysisDataError), analysis.transaction():
        analysis.relink_source_video(first.id, "/videos/second-half.mp4")

    assert analysis.revision == revision
    assert analysis.source_video(first.id).location == "/videos/first-half.mp4"


def test_removing_a_source_video_with_clips_reports_how_many_it_takes_with_it() -> None:
    analysis = _analysis_with_source()
    source_video = analysis.source_videos[0]
    analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    analysis.add_clip(source_video.id, "Turnover", 3_000, 4_000)

    assert len(analysis.clips_of_source_video(source_video.id)) == 2

    analysis.remove_source_video(source_video.id)

    assert analysis.clips == ()


def test_removing_the_last_source_video_leaves_an_empty_analysis_still_valid() -> None:
    analysis = _analysis_with_source()
    source_video = analysis.source_videos[0]

    analysis.remove_source_video(source_video.id)

    assert analysis.source_videos == ()
    assert analysis.title == "Match"
    assert analysis.clips == ()


def test_a_clip_may_not_exceed_its_source_video_duration() -> None:
    analysis = Analysis("Match")
    source_video = analysis.add_source_video(
        "first-half.mp4",
        "/videos/a.mp4",
        duration_ms=5_000,
    )
    clip = analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)

    with pytest.raises(InvalidAnalysisDataError):
        analysis.update_clip(clip.id, end_ms=6_000)


def test_category_lookup_by_name_is_case_insensitive() -> None:
    analysis = _analysis_with_source()
    category = analysis.add_category("Angriff", "#EF4444")

    assert analysis.category_named(" angriff ") == category
    assert analysis.category_named("Tor") is None


def test_documents_expose_dirty_state_from_content_revisions(tmp_path) -> None:
    document = new_analysis_document("Match")
    analysis = document.analysis
    source_video = analysis.add_source_video("a.mp4", "/videos/a.mp4")

    assert document.dirty is True

    path = document.save_as(tmp_path / "match.analysis")
    assert document.dirty is False

    clip = analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    assert document.dirty is True

    document.save()
    assert document.dirty is False

    reopened = AnalysisDocument.new()
    reopened.load(path)

    assert reopened.analysis.id == analysis.id
    assert reopened.analysis.title == "Match"
    assert [existing.id for existing in reopened.analysis.clips] == [clip.id]
    assert [existing.id for existing in reopened.analysis.source_videos] == [
        source_video.id
    ]
    assert reopened.dirty is False
