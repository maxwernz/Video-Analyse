from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest

from analysis import (
    Analysis,
    AnalysisDocument,
    ExternalChangeChoice,
    RecoverySnapshotStore,
    UnsavedChangesChoice,
    new_analysis_document,
)
from application_workflow import ApplicationWorkflow
from media_probe import ProbedMedia


class FakePresenter:
    """Stands in for every decision the workflow asks a person to make."""

    def __init__(self) -> None:
        self.unsaved_choice = UnsavedChangesChoice.DISCARD
        self.external_change_choice = ExternalChangeChoice.CANCEL
        self.recovery_offer_accepted = False
        self.analysis_to_open: str | None = None
        self.analysis_destination: str | None = None
        self.source_video: str | None = None
        self.replacement_media: str | None = None
        self.replacement_confirmed = False
        self.unsaved_prompts = 0
        self.external_change_prompts = 0
        self.recovery_offers = 0
        self.replacement_confirmation_prompts = 0
        self.replacement_confirmation_names: list[str] = []
        self.suggested_names: list[str] = []
        self.failures: list[tuple[str, str]] = []

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        self.unsaved_prompts += 1
        return self.unsaved_choice

    def ask_external_change_conflict(self) -> ExternalChangeChoice:
        self.external_change_prompts += 1
        return self.external_change_choice

    def offer_recovered_analysis(self) -> bool:
        self.recovery_offers += 1
        return self.recovery_offer_accepted

    def choose_analysis_to_open(self) -> str | None:
        return self.analysis_to_open

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        self.suggested_names.append(suggested_name)
        return self.analysis_destination

    def choose_source_video(self) -> str | None:
        return self.source_video

    def choose_replacement_media(self, display_name: str) -> str | None:
        return self.replacement_media

    def confirm_source_video_replacement(self, display_name: str) -> bool:
        self.replacement_confirmation_prompts += 1
        self.replacement_confirmation_names.append(display_name)
        return self.replacement_confirmed

    def report_failure(self, title: str, message: str) -> None:
        self.failures.append((title, message))


class FakeRecoveryScheduler:
    """Records scheduling and cancellation without any real timer."""

    def __init__(self) -> None:
        self.scheduled_runs: list[Callable[[], None]] = []
        self.cancel_count = 0
        self._pending: Callable[[], None] | None = None

    def schedule(self, run: Callable[[], None]) -> None:
        self.scheduled_runs.append(run)
        self._pending = run

    def cancel(self) -> None:
        self.cancel_count += 1
        self._pending = None

    def fire(self) -> None:
        """Simulate the debounce settling: run whatever is still pending."""
        assert self._pending is not None, "nothing was scheduled"
        pending, self._pending = self._pending, None
        pending()


class RecordedEvents:
    def __init__(self) -> None:
        self.replacements = 0
        self.changes = 0


class FakeMediaProbe:
    """Reports whatever `ProbedMedia` a test pins to a path, no bytes read.

    Mirrors the parent Analysis-document spec's fake player/probe seam: a
    controller test can then assert duplicate-rejection and relink behaviour
    against exact byte size, duration and fingerprint values without a real
    video file to decode.
    """

    def __init__(self) -> None:
        self.by_path: dict[Path, ProbedMedia] = {}
        self.unreadable: set[Path] = set()
        self.default = ProbedMedia(byte_size=1, fingerprint="fake", duration_ms=None)

    def probe(self, path: Path) -> ProbedMedia:
        if path in self.unreadable:
            raise OSError(f"cannot read {path}")
        return self.by_path.get(path, self.default)


@pytest.fixture
def presenter() -> FakePresenter:
    return FakePresenter()


@pytest.fixture
def events() -> RecordedEvents:
    return RecordedEvents()


@pytest.fixture
def recovery_store(tmp_path: Path) -> RecoverySnapshotStore:
    # Isolated from any real installation location, so a test's `save` or
    # `discard_recovery` call can never touch a real analyst's Recovery data.
    return RecoverySnapshotStore(tmp_path / "recovery-store")


@pytest.fixture
def recovery_scheduler() -> FakeRecoveryScheduler:
    return FakeRecoveryScheduler()


@pytest.fixture
def workflow(
    presenter: FakePresenter,
    events: RecordedEvents,
    recovery_store: RecoverySnapshotStore,
    recovery_scheduler: FakeRecoveryScheduler,
) -> ApplicationWorkflow:
    def analysis_replaced() -> None:
        events.replacements += 1

    def document_changed() -> None:
        events.changes += 1

    return ApplicationWorkflow(
        presenter,
        on_analysis_replaced=analysis_replaced,
        on_document_changed=document_changed,
        recovery_store=recovery_store,
        recovery_scheduler=recovery_scheduler,
    )


def _video(tmp_path: Path, name: str = "first-half.mp4") -> Path:
    """A file distinct enough for the fingerprinting probe to tell apart.

    Every call with a different ``name`` must produce different sampled
    content: the probe combines sampled bytes with size, and two files this
    small are read in full, so the name has to be part of what gets hashed
    rather than just what the file is called.
    """
    video_path = tmp_path / name
    video_path.write_bytes(f"not a real video: {name}".encode())
    return video_path


def _analysis_with_work(workflow: ApplicationWorkflow, tmp_path: Path) -> None:
    source_video = workflow.add_source_video_file(_video(tmp_path))
    assert source_video is not None
    workflow.analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)


# --- New ------------------------------------------------------------------


def test_a_new_workflow_starts_on_a_clean_templated_analysis(
    workflow: ApplicationWorkflow,
) -> None:
    assert workflow.analysis.source_videos == ()
    assert [category.name for category in workflow.analysis.categories] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]
    assert workflow.document.dirty is False


def test_new_analysis_replaces_the_current_one_after_discarding(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    assert workflow.new_analysis() is True

    assert presenter.unsaved_prompts == 1
    assert workflow.analysis.clips == ()
    assert workflow.analysis.source_videos == ()
    assert workflow.document.dirty is False
    assert events.replacements == 1


def test_cancelling_the_unsaved_prompt_keeps_the_current_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    analysis = workflow.analysis
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL

    assert workflow.new_analysis() is False

    assert workflow.analysis is analysis
    assert len(workflow.analysis.clips) == 1
    assert events.replacements == 0


def test_a_clean_analysis_is_replaced_without_asking(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    assert workflow.new_analysis() is True
    assert presenter.unsaved_prompts == 0


# --- Save and Save As -----------------------------------------------------


def test_saving_an_unsaved_analysis_asks_for_a_destination_once(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    destination = tmp_path / "match.analysis"
    presenter.analysis_destination = str(destination)

    assert workflow.save() is True
    assert destination.is_file()
    assert workflow.document.dirty is False
    assert presenter.suggested_names == ["first-half.analysis"]

    workflow.analysis.add_clip(
        workflow.analysis.source_videos[0].id, "Second", 3_000, 4_000
    )
    assert workflow.save() is True
    assert presenter.suggested_names == ["first-half.analysis"]


def test_save_as_always_asks_for_a_destination(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.analysis_destination = str(tmp_path / "match.analysis")
    assert workflow.save() is True

    presenter.analysis_destination = str(tmp_path / "copy.analysis")
    assert workflow.save_as() is True

    assert (tmp_path / "copy.analysis").is_file()
    assert workflow.document.path == tmp_path / "copy.analysis"
    assert len(presenter.suggested_names) == 2


def test_a_cancelled_destination_leaves_the_analysis_dirty(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.analysis_destination = None

    assert workflow.save() is False
    assert workflow.document.dirty is True
    assert presenter.failures == []


def test_a_failed_save_is_reported_and_leaves_the_analysis_dirty(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    workflow.analysis.set_title("Leer")
    presenter.analysis_destination = str(tmp_path / "empty.analysis")

    assert workflow.save() is False
    assert workflow.document.dirty is True
    assert len(presenter.failures) == 1
    assert not (tmp_path / "empty.analysis").exists()


def test_a_cancelled_save_prevents_replacing_the_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.SAVE
    presenter.analysis_destination = None

    assert workflow.new_analysis() is False
    assert workflow.document.dirty is True
    assert len(workflow.analysis.clips) == 1


def test_a_failed_save_prevents_replacing_the_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    workflow.analysis.set_title("Leer")
    presenter.unsaved_choice = UnsavedChangesChoice.SAVE
    presenter.analysis_destination = str(tmp_path / "empty.analysis")

    assert workflow.new_analysis() is False
    assert workflow.document.dirty is True


def test_saving_before_replacing_lets_the_analysis_go(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.SAVE
    presenter.analysis_destination = str(tmp_path / "match.analysis")

    assert workflow.new_analysis() is True
    assert (tmp_path / "match.analysis").is_file()
    assert workflow.analysis.clips == ()


# --- Open -----------------------------------------------------------------


def _saved_analysis_file(tmp_path: Path) -> Path:
    document = new_analysis_document("Gespeichert")
    source_video = document.analysis.add_source_video(
        "second-half.mp4",
        str(tmp_path / "second-half.mp4"),
    )
    document.analysis.add_clip(source_video.id, "Tor", 5_000, 6_000)
    return document.save_as(tmp_path / "saved.analysis")


def test_opening_an_analysis_replaces_the_current_one(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    saved = _saved_analysis_file(tmp_path)
    presenter.analysis_to_open = str(saved)

    assert workflow.open_analysis() is True

    assert workflow.analysis.title == "Gespeichert"
    assert [clip.name for clip in workflow.analysis.clips] == ["Tor"]
    assert workflow.document.path == saved
    assert workflow.document.dirty is False
    assert events.replacements == 1


def test_unsaved_changes_are_settled_before_a_file_is_chosen(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    """Nobody should pick a file only to be asked whether they meant to."""
    _analysis_with_work(workflow, tmp_path)
    asked: list[str] = []
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL
    presenter.analysis_to_open = str(_saved_analysis_file(tmp_path))

    def record_prompt() -> UnsavedChangesChoice:
        asked.append("unsaved")
        return UnsavedChangesChoice.CANCEL

    def record_chooser() -> str | None:
        asked.append("chooser")
        return presenter.analysis_to_open

    presenter.ask_unsaved_changes = record_prompt  # type: ignore[method-assign]
    presenter.choose_analysis_to_open = record_chooser  # type: ignore[method-assign]

    assert workflow.open_analysis() is False

    assert asked == ["unsaved"]


def test_cancelling_the_open_dialog_changes_nothing(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    events: RecordedEvents,
) -> None:
    presenter.analysis_to_open = None

    assert workflow.open_analysis() is False
    assert events.replacements == 0
    assert presenter.unsaved_prompts == 0


def test_a_failed_load_leaves_the_open_analysis_untouched(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    analysis = workflow.analysis
    broken = tmp_path / "broken.analysis"
    broken.write_text("{ not json", encoding="utf-8")
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    assert workflow.open_analysis_file(broken) is False

    assert workflow.analysis is analysis
    assert len(workflow.analysis.clips) == 1
    assert len(presenter.failures) == 1
    assert events.replacements == 0


def test_a_rejected_load_leaves_the_open_analysis_untouched(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    analysis = workflow.analysis
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL

    assert workflow.open_analysis_file(_saved_analysis_file(tmp_path)) is False

    assert workflow.analysis is analysis
    assert len(workflow.analysis.clips) == 1


def test_a_missing_analysis_file_is_reported(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    assert workflow.open_analysis_file(tmp_path / "absent.analysis") is False
    assert len(presenter.failures) == 1


# --- Adding Source videos -------------------------------------------------


def test_adding_a_video_is_additive_and_keeps_existing_work(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
    presenter: FakePresenter,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    changes_before = events.changes

    second = workflow.add_source_video_file(_video(tmp_path, "second-half.mp4"))

    assert second is not None
    assert [source.display_name for source in workflow.analysis.source_videos] == [
        "first-half.mp4",
        "second-half.mp4",
    ]
    assert len(workflow.analysis.clips) == 1
    assert presenter.unsaved_prompts == 0
    assert events.replacements == 0
    assert events.changes == changes_before + 1


def test_only_the_first_video_titles_an_untitled_analysis(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    workflow.add_source_video_file(_video(tmp_path))
    workflow.add_source_video_file(_video(tmp_path, "second-half.mp4"))

    assert workflow.analysis.title == "first-half"


def test_adding_a_video_through_the_dialog_uses_the_chosen_file(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    presenter.source_video = str(_video(tmp_path))

    added = workflow.add_source_video()

    assert added is not None
    assert workflow.analysis.source_videos[0].location == presenter.source_video


def test_cancelling_the_video_dialog_adds_nothing(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    presenter.source_video = None

    assert workflow.add_source_video() is None
    assert workflow.analysis.source_videos == ()


def test_a_rejected_video_is_reported_and_leaves_the_analysis_as_it_was(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    video_path = _video(tmp_path)
    workflow.add_source_video_file(video_path)
    revision = workflow.analysis.revision

    assert workflow.add_source_video_file(video_path) is None

    assert len(workflow.analysis.source_videos) == 1
    assert workflow.analysis.revision == revision
    assert len(presenter.failures) == 1


def test_a_rejected_first_video_does_not_leave_a_title_behind(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    assert workflow.add_source_video_file(tmp_path / "   ") is None

    assert workflow.analysis.title == ""
    assert workflow.analysis.source_videos == ()
    assert workflow.document.dirty is False


def test_starting_a_new_analysis_is_not_the_same_as_adding_a_video(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    workflow.new_analysis()

    assert workflow.analysis.source_videos == ()
    assert workflow.analysis.clips == ()


# --- Dropped files --------------------------------------------------------


def test_a_dropped_video_is_added_to_the_current_analysis(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)

    assert workflow.open_dropped_file(_video(tmp_path, "second-half.MOV")) is True

    assert len(workflow.analysis.source_videos) == 2
    assert len(workflow.analysis.clips) == 1


def test_a_dropped_analysis_file_replaces_the_current_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    assert workflow.open_dropped_file(_saved_analysis_file(tmp_path)) is True

    assert workflow.analysis.title == "Gespeichert"


def test_an_unsupported_dropped_file_is_ignored(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    note = tmp_path / "notes.txt"
    note.write_text("nothing to see", encoding="utf-8")

    assert workflow.open_dropped_file(note) is False
    assert workflow.analysis.source_videos == ()


# --- Window title ---------------------------------------------------------


def test_the_window_title_reports_an_untitled_clean_analysis(
    workflow: ApplicationWorkflow,
) -> None:
    assert workflow.window_title == "Unbenannte Analyse — Video Analyse"


def test_the_window_title_reports_the_title_and_dirty_state(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    assert workflow.window_title == "• first-half — Video Analyse"

    workflow.analysis.set_title("Spiel gegen Musterstadt")
    assert workflow.window_title == "• Spiel gegen Musterstadt — Video Analyse"

    presenter.analysis_destination = str(tmp_path / "match.analysis")
    assert workflow.save() is True
    assert workflow.window_title == "Spiel gegen Musterstadt — Video Analyse"


# --- Closing --------------------------------------------------------------


def test_closing_a_clean_analysis_is_allowed_without_asking(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    assert workflow.may_replace_analysis() is True
    assert presenter.unsaved_prompts == 0


def test_closing_a_dirty_analysis_asks_and_can_be_refused(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL

    assert workflow.may_replace_analysis() is False
    assert workflow.document.dirty is True


def test_an_explicitly_supplied_document_is_adopted(
    presenter: FakePresenter,
) -> None:
    document = AnalysisDocument(Analysis("Vorhanden"))

    workflow = ApplicationWorkflow(presenter, document=document)

    assert workflow.document is document
    assert workflow.analysis.title == "Vorhanden"


# --- Source-video identity and lifecycle -----------------------------------


def test_adding_a_video_records_its_probed_identity(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    video_path = _video(tmp_path)
    probe.by_path[video_path] = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=2_700_000
    )
    workflow = ApplicationWorkflow(presenter, media_probe=probe)

    source_video = workflow.add_source_video_file(video_path)

    assert source_video is not None
    assert source_video.byte_size == 999
    assert source_video.fingerprint == "sampled-sha256:abc"
    assert source_video.duration_ms == 2_700_000


def test_adding_the_exact_same_media_again_is_rejected_as_a_duplicate(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    video_path = _video(tmp_path)
    probe.by_path[video_path] = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=1_000
    )
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    workflow.add_source_video_file(video_path)
    revision = workflow.analysis.revision

    added_again = workflow.add_source_video_file(video_path)

    assert added_again is None
    assert len(workflow.analysis.source_videos) == 1
    assert workflow.analysis.revision == revision
    assert len(presenter.failures) == 1


def test_a_moved_source_video_relinks_instead_of_duplicating(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    original_path = tmp_path / "match.mp4"
    original_path.write_bytes(b"original")
    identity = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=2_700_000
    )
    probe.by_path[original_path] = identity
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    original = workflow.add_source_video_file(original_path)
    assert original is not None
    clip = workflow.analysis.add_clip(original.id, "Fast break", 1_000, 2_000)

    moved_directory = tmp_path / "moved"
    moved_directory.mkdir()
    moved_path = moved_directory / "match.mp4"
    moved_path.write_bytes(b"same content, new home")
    probe.by_path[moved_path] = identity

    relinked = workflow.add_source_video_file(moved_path)

    assert relinked is not None
    assert relinked.id == original.id
    assert relinked.location == str(moved_path)
    assert len(workflow.analysis.source_videos) == 1
    assert workflow.analysis.clip(clip.id).source_video_id == original.id
    assert presenter.failures == []


# --- Relinking an unavailable Source video ----------------------------------


def test_a_source_video_with_no_file_at_its_location_is_unavailable(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    video_path = _video(tmp_path)
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(video_path)
    assert source_video is not None

    video_path.unlink()

    assert workflow.is_source_video_available(source_video.id) is False


def test_a_verified_match_relinks_without_asking_for_confirmation(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    original_path = tmp_path / "match.mp4"
    original_path.write_bytes(b"original")
    identity = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=2_700_000
    )
    probe.by_path[original_path] = identity
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(original_path)
    assert source_video is not None
    clip = workflow.analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    original_path.unlink()

    replacement_path = tmp_path / "recovered.mp4"
    replacement_path.write_bytes(b"recovered copy")
    probe.by_path[replacement_path] = identity

    relinked = workflow.relink_source_video_file(source_video.id, replacement_path)

    assert relinked is True
    assert presenter.replacement_confirmation_prompts == 0
    assert workflow.is_source_video_available(source_video.id) is True
    assert workflow.analysis.source_video(source_video.id).location == str(
        replacement_path
    )
    assert workflow.analysis.clip(clip.id).source_video_id == source_video.id
    assert presenter.failures == []


def test_a_mismatched_replacement_requires_explicit_confirmation(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    original_path = tmp_path / "match.mp4"
    original_path.write_bytes(b"original")
    probe.by_path[original_path] = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=2_700_000
    )
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(original_path)
    assert source_video is not None
    original_path.unlink()

    unrelated_path = tmp_path / "unrelated.mp4"
    unrelated_path.write_bytes(b"something else entirely")
    probe.by_path[unrelated_path] = ProbedMedia(
        byte_size=12, fingerprint="sampled-sha256:different", duration_ms=500
    )
    presenter.replacement_confirmed = True

    relinked = workflow.relink_source_video_file(source_video.id, unrelated_path)

    assert relinked is True
    assert presenter.replacement_confirmation_prompts == 1
    assert presenter.replacement_confirmation_names == [source_video.display_name]
    assert workflow.analysis.source_video(source_video.id).fingerprint == (
        "sampled-sha256:different"
    )


def test_declining_the_mismatch_confirmation_leaves_the_source_video_unavailable(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    original_path = tmp_path / "match.mp4"
    original_path.write_bytes(b"original")
    probe.by_path[original_path] = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=2_700_000
    )
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(original_path)
    assert source_video is not None
    clip = workflow.analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    original_path.unlink()
    revision = workflow.analysis.revision

    unrelated_path = tmp_path / "unrelated.mp4"
    unrelated_path.write_bytes(b"something else entirely")
    probe.by_path[unrelated_path] = ProbedMedia(
        byte_size=12, fingerprint="sampled-sha256:different", duration_ms=500
    )
    presenter.replacement_confirmed = False

    relinked = workflow.relink_source_video_file(source_video.id, unrelated_path)

    assert relinked is False
    assert workflow.analysis.revision == revision
    assert workflow.analysis.source_video(source_video.id).location == str(
        original_path
    )
    assert workflow.analysis.clip(clip.id).source_video_id == source_video.id
    assert workflow.is_source_video_available(source_video.id) is False


def test_relinking_an_unknown_source_video_is_reported_rather_than_raised(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    """A stale Source-video id must be reported, not raised past the Slot.

    `relink_source_video` looks the Source video up first, to name it in the
    replacement-media dialog; that lookup can fail exactly like every other
    domain call in this module, and must fail the same way — reported to the
    presenter — rather than letting `UnknownEntityError` escape uncaught.
    """
    assert workflow.relink_source_video(uuid4()) is False
    assert len(presenter.failures) == 1


def test_a_cancelled_relink_dialog_leaves_the_source_video_unavailable(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    video_path = _video(tmp_path)
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(video_path)
    assert source_video is not None
    video_path.unlink()
    presenter.replacement_media = None

    relinked = workflow.relink_source_video(source_video.id)

    assert relinked is False
    assert presenter.replacement_confirmation_prompts == 0
    assert workflow.is_source_video_available(source_video.id) is False


def test_a_failed_probe_during_relink_leaves_the_source_video_unavailable(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    video_path = _video(tmp_path)
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(video_path)
    assert source_video is not None
    video_path.unlink()
    unreadable_path = tmp_path / "corrupt.mp4"
    probe.unreadable.add(unreadable_path)

    relinked = workflow.relink_source_video_file(source_video.id, unreadable_path)

    assert relinked is False
    assert len(presenter.failures) == 1
    assert workflow.is_source_video_available(source_video.id) is False


def test_relinking_records_a_relative_path_for_a_future_moved_together_open(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    probe = FakeMediaProbe()
    videos_directory = tmp_path / "videos"
    videos_directory.mkdir()
    original_path = videos_directory / "match.mp4"
    original_path.write_bytes(b"original")
    identity = ProbedMedia(
        byte_size=999, fingerprint="sampled-sha256:abc", duration_ms=2_700_000
    )
    probe.by_path[original_path] = identity
    workflow = ApplicationWorkflow(presenter, media_probe=probe)
    source_video = workflow.add_source_video_file(original_path)
    assert source_video is not None
    workflow.document.save_as(tmp_path / "match.analysis")
    original_path.unlink()

    replacement_path = videos_directory / "recovered.mp4"
    replacement_path.write_bytes(b"recovered copy")
    probe.by_path[replacement_path] = identity

    relinked = workflow.relink_source_video_file(source_video.id, replacement_path)

    assert relinked is True
    assert workflow.analysis.source_video(source_video.id).relative_path == (
        "videos/recovered.mp4"
    )


def test_renaming_a_source_video_keeps_its_clips(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    source_video = workflow.analysis.source_videos[0]
    clip = workflow.analysis.clips[0]
    changes_before = events.changes

    renamed = workflow.rename_source_video(source_video.id, "Halbzeit 1")

    assert renamed is True
    assert workflow.analysis.source_video(source_video.id).display_name == (
        "Halbzeit 1"
    )
    assert workflow.analysis.clip(clip.id).source_video_id == source_video.id
    assert events.changes == changes_before + 1


def test_renaming_a_source_video_to_an_empty_name_is_reported_and_rejected(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    source_video = workflow.analysis.source_videos[0]

    assert workflow.rename_source_video(source_video.id, "   ") is False

    assert workflow.analysis.source_video(source_video.id).display_name == (
        source_video.display_name
    )
    assert len(presenter.failures) == 1


def test_reordering_source_videos_sets_the_durable_display_order(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    first = workflow.add_source_video_file(_video(tmp_path))
    second = workflow.add_source_video_file(_video(tmp_path, "second-half.mp4"))
    assert first is not None and second is not None

    assert workflow.reorder_source_videos([second.id, first.id]) is True

    assert [source.id for source in workflow.analysis.source_videos] == [
        second.id,
        first.id,
    ]


def test_removing_a_source_video_without_clips_leaves_no_trace_of_it(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    source_video = workflow.add_source_video_file(_video(tmp_path))
    assert source_video is not None
    assert workflow.clip_count_for_source_video(source_video.id) == 0

    assert workflow.remove_source_video(source_video.id) is True

    assert workflow.analysis.source_videos == ()


def test_removing_a_source_video_reports_and_takes_its_clips_with_it(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    source_video = workflow.analysis.source_videos[0]
    workflow.analysis.add_clip(source_video.id, "Turnover", 3_000, 4_000)

    assert workflow.clip_count_for_source_video(source_video.id) == 2

    assert workflow.remove_source_video(source_video.id) is True

    assert workflow.analysis.source_videos == ()
    assert workflow.analysis.clips == ()


def test_removed_source_video_is_reported_through_its_own_callback(
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    removed_ids: list = []
    workflow = ApplicationWorkflow(
        presenter, on_source_video_removed=removed_ids.append
    )
    source_video = workflow.add_source_video_file(_video(tmp_path))
    assert source_video is not None

    assert workflow.remove_source_video(source_video.id) is True

    assert removed_ids == [source_video.id]


def test_removing_an_unknown_source_video_is_reported_and_changes_nothing(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    from uuid import uuid4

    assert workflow.remove_source_video(uuid4()) is False
    assert len(presenter.failures) == 1


# --- External-change conflicts ---------------------------------------------


def _saved_workflow_with_external_change(
    workflow: ApplicationWorkflow, presenter: FakePresenter, tmp_path: Path
) -> None:
    """Save, then simulate another process changing the file underneath us."""
    _analysis_with_work(workflow, tmp_path)
    presenter.analysis_destination = str(tmp_path / "match.analysis")
    assert workflow.save() is True

    assert workflow.document.path is not None
    saved_path = workflow.document.path
    import os

    os.utime(saved_path, ns=(0, 10**18))
    saved_path.write_bytes(saved_path.read_bytes() + b"\n")

    workflow.analysis.set_title("Local unsaved edit")


def test_saving_over_an_externally_changed_file_asks_instead_of_overwriting(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _saved_workflow_with_external_change(workflow, presenter, tmp_path)
    external_bytes = workflow.document.path.read_bytes()  # type: ignore[union-attr]
    presenter.external_change_choice = ExternalChangeChoice.CANCEL

    assert workflow.save() is False

    assert presenter.external_change_prompts == 1
    assert workflow.document.dirty is True
    assert workflow.document.path.read_bytes() == external_bytes  # type: ignore[union-attr]


def test_choosing_reload_on_conflict_discards_local_edits(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _saved_workflow_with_external_change(workflow, presenter, tmp_path)
    presenter.external_change_choice = ExternalChangeChoice.RELOAD

    assert workflow.save() is True

    assert workflow.analysis.title != "Local unsaved edit"
    assert workflow.document.dirty is False
    assert events.replacements >= 1


def test_choosing_save_as_on_conflict_keeps_local_edits_under_a_new_name(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _saved_workflow_with_external_change(workflow, presenter, tmp_path)
    external_bytes = workflow.document.path.read_bytes()  # type: ignore[union-attr]
    presenter.external_change_choice = ExternalChangeChoice.SAVE_AS
    presenter.analysis_destination = str(tmp_path / "match-mine.analysis")

    assert workflow.save() is True

    assert workflow.analysis.title == "Local unsaved edit"
    assert workflow.document.dirty is False
    assert workflow.document.path == tmp_path / "match-mine.analysis"
    # The externally changed file is never touched.
    assert (tmp_path / "match.analysis").read_bytes() == external_bytes


# --- Debounced Recovery scheduling ------------------------------------------


def test_a_durable_change_schedules_a_recovery_snapshot(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
    recovery_store: RecoverySnapshotStore,
    recovery_scheduler: "FakeRecoveryScheduler",
) -> None:
    _analysis_with_work(workflow, tmp_path)
    workflow.note_recovery_activity()

    assert len(recovery_scheduler.scheduled_runs) == 1
    assert recovery_store.read() is None  # not written until the debounce fires

    recovery_scheduler.fire()

    snapshot = recovery_store.read()
    assert snapshot is not None
    assert len(snapshot.analysis.clips) == 1


def test_repeated_activity_before_the_debounce_fires_collapses_to_one_write(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
    recovery_scheduler: "FakeRecoveryScheduler",
) -> None:
    source_video = workflow.add_source_video_file(_video(tmp_path))
    assert source_video is not None
    workflow.note_recovery_activity()
    workflow.analysis.add_clip(source_video.id, "First", 1_000, 2_000)
    workflow.note_recovery_activity()
    workflow.analysis.add_clip(source_video.id, "Second", 3_000, 4_000)
    workflow.note_recovery_activity()

    # Three durable changes, but each `note_recovery_activity` call replaces
    # whatever was scheduled: the fake records every call, mirroring a real
    # debounce timer restarting rather than queuing.
    assert len(recovery_scheduler.scheduled_runs) == 3
    assert recovery_scheduler.cancel_count == 0


def test_view_only_activity_never_schedules_a_recovery_snapshot(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
    recovery_scheduler: "FakeRecoveryScheduler",
) -> None:
    _analysis_with_work(workflow, tmp_path)
    workflow.note_recovery_activity()
    recovery_scheduler.scheduled_runs.clear()

    # Nothing durable happens between these calls: no Analysis mutation, so
    # no revision change, so no rescheduling — exactly what protects
    # playback, the Active Source video, selection, and sidebar-tab state.
    workflow.note_recovery_activity()
    workflow.note_recovery_activity()

    assert recovery_scheduler.scheduled_runs == []


def test_a_successful_save_discards_pending_and_stored_recovery_data(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    recovery_store: RecoverySnapshotStore,
    recovery_scheduler: "FakeRecoveryScheduler",
) -> None:
    _analysis_with_work(workflow, tmp_path)
    workflow.note_recovery_activity()
    recovery_scheduler.fire()
    assert recovery_store.read() is not None

    presenter.analysis_destination = str(tmp_path / "match.analysis")
    assert workflow.save() is True

    assert recovery_store.read() is None
    assert recovery_scheduler.cancel_count >= 1


def test_a_deliberate_discard_removes_recovery_data(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    recovery_store: RecoverySnapshotStore,
    recovery_scheduler: "FakeRecoveryScheduler",
) -> None:
    _analysis_with_work(workflow, tmp_path)
    workflow.note_recovery_activity()
    recovery_scheduler.fire()
    assert recovery_store.read() is not None

    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD
    assert workflow.new_analysis() is True

    assert recovery_store.read() is None


# --- Abnormal-termination recovery ------------------------------------------


def test_no_stored_snapshot_offers_nothing(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    assert workflow.recover_if_available() is False
    assert presenter.recovery_offers == 0


def test_a_declined_recovery_offer_discards_the_snapshot(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    recovery_store: RecoverySnapshotStore,
) -> None:
    unsaved_analysis = Analysis("Unsaved")
    unsaved_analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    recovery_store.write(unsaved_analysis, None)
    presenter.recovery_offer_accepted = False

    assert workflow.recover_if_available() is False

    assert presenter.recovery_offers == 1
    assert recovery_store.read() is None


def test_an_accepted_recovery_offer_replaces_the_analysis_and_stays_dirty(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    events: RecordedEvents,
    recovery_store: RecoverySnapshotStore,
) -> None:
    recovered_analysis = Analysis("Recovered work")
    recovered_analysis.add_source_video(
        "first-half.mp4", "/videos/first-half.mp4"
    )
    recovery_store.write(recovered_analysis, None)
    presenter.recovery_offer_accepted = True

    assert workflow.recover_if_available() is True

    assert workflow.analysis.title == "Recovered work"
    assert workflow.document.dirty is True
    assert events.replacements >= 1
    # Re-armed immediately: the just-restored work is still unsaved, and
    # nothing will edit it again to trigger `note_recovery_activity` itself.
    restored_snapshot = recovery_store.read()
    assert restored_snapshot is not None
    assert restored_snapshot.analysis.title == "Recovered work"


def test_an_accepted_recovery_offer_keeps_the_file_it_was_bound_to(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    recovery_store: RecoverySnapshotStore,
    tmp_path: Path,
) -> None:
    """The restored Analysis still knows which file it was being edited as."""

    # The file this Analysis was open as when the process died — still on
    # disk, unchanged, exactly as an abnormal termination would leave it.
    original_path = tmp_path / "match.analysis"
    original_document = AnalysisDocument.new("On disk when it crashed")
    original_document.analysis.add_source_video(
        "first-half.mp4", "/videos/first-half.mp4"
    )
    original_document.save_as(original_path)

    recovered_analysis = Analysis("Recovered work")
    recovered_analysis.add_source_video(
        "first-half.mp4", "/videos/first-half.mp4"
    )
    recovery_store.write(recovered_analysis, original_path)
    presenter.recovery_offer_accepted = True

    assert workflow.recover_if_available() is True

    assert workflow.document.path == original_path
    # With no recorded revision for this file, a plain Save must not assume
    # nothing changed since the abnormal termination — it asks instead.
    presenter.external_change_choice = ExternalChangeChoice.SAVE_AS
    presenter.analysis_destination = str(tmp_path / "match-restored.analysis")

    original_bytes = original_path.read_bytes()

    assert workflow.save() is True

    assert presenter.external_change_prompts == 1
    # The original file is left exactly as it was; the restored work is
    # kept under a name of its own rather than overwriting it.
    assert original_path.read_bytes() == original_bytes
    assert (tmp_path / "match-restored.analysis").is_file()
