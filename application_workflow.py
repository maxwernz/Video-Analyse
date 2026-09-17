"""The application workflow layer over one Analysis document.

This module owns the document commands — New, Open, Save, Save As, and Close —
the unsaved-changes decision flow, and additive Source-video adding. It reports
the window title, so the interface above it renders a decision rather than
making one.

It deliberately holds no user-interface types. Everything it needs from a person
arrives through a :class:`WorkflowPresenter`, and everything the interface needs
to redraw arrives as one of three notifications, which keeps the whole layer
testable without widgets, dialogs, or media.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol
from uuid import UUID

from analysis import (
    Analysis,
    AnalysisDocument,
    AnalysisError,
    ExternalChangeChoice,
    RecoverySnapshotStore,
    SourceVideo,
    UnsavedChangesChoice,
    CategoryTemplateStore,
    new_analysis_document,
)
from category_template_settings import installation_category_template_store
from media_probe import FileMediaProbe, MediaProbe
from recovery_settings import installation_recovery_store

APPLICATION_TITLE = "Video Analyse"
UNTITLED_ANALYSIS_TITLE = "Unbenannte Analyse"
UNSAVED_CHANGES_MARKER = "•"

ANALYSIS_FILE_SUFFIX = ".analysis"
SOURCE_VIDEO_SUFFIXES = (".mp4", ".mov")

#: File-dialog filters, so a dialog and a dropped file accept the same files.
ANALYSIS_FILE_FILTER = f"Analyse Dateien (*{ANALYSIS_FILE_SUFFIX})"
SOURCE_VIDEO_FILE_FILTER = "Video Dateien ({})".format(
    " ".join(f"*{suffix}" for suffix in SOURCE_VIDEO_SUFFIXES)
)

_FALLBACK_ANALYSIS_FILE_NAME = "Analyse"


class WorkflowPresenter(Protocol):
    """Every decision the workflow asks a person to make, and every report.

    A chooser returns ``None`` when the person dismissed the dialog, which the
    workflow treats as cancelling the command rather than as a failure.
    """

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        """Ask what should happen to unsaved Analysis changes."""

    def ask_external_change_conflict(self) -> ExternalChangeChoice:
        """Ask how to resolve an Analysis file changed outside the application."""

    def offer_recovered_analysis(self) -> bool:
        """Ask whether to restore Recovery data found after abnormal termination.

        Returning ``False`` — including a dismissed prompt — is read as
        declining it, which discards the offered snapshot rather than
        leaving it to be offered again unexplained next time.
        """

    def choose_analysis_to_open(self) -> str | None:
        """Ask which Analysis file to open."""

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        """Ask where to write the Analysis file."""

    def choose_source_video(self) -> str | None:
        """Ask which video file to add as a Source video."""

    def report_failure(self, title: str, message: str) -> None:
        """Report that a command could not be carried out."""


class RecoveryScheduler(Protocol):
    """Runs Recovery work once change activity has settled.

    Calling :meth:`schedule` again before it has run replaces whatever was
    pending, which is what makes this a debounce rather than a delay: rapid
    edits collapse into the one snapshot due after the last of them. The
    real implementation is a restartable Qt timer, built where the rest of
    this workflow's Qt timing lives; the default here does nothing, so a
    bare `ApplicationWorkflow` built without one — as most of this module's
    own tests do — never schedules Recovery work nobody asked it to.
    """

    def schedule(self, run: Callable[[], None]) -> None: ...

    def cancel(self) -> None: ...


class _NoRecoveryScheduling:
    """The scheduler a workflow gets when none is supplied: it never fires."""

    def schedule(self, run: Callable[[], None]) -> None:
        return None

    def cancel(self) -> None:
        return None


class ApplicationWorkflow:
    """Drives the lifecycle of exactly one open Analysis document."""

    def __init__(
        self,
        presenter: WorkflowPresenter,
        *,
        document: AnalysisDocument | None = None,
        on_analysis_replaced: Callable[[], None] | None = None,
        on_document_changed: Callable[[], None] | None = None,
        on_source_video_added: Callable[[SourceVideo], None] | None = None,
        on_source_video_removed: Callable[[UUID], None] | None = None,
        media_probe: MediaProbe | None = None,
        template_store: CategoryTemplateStore | None = None,
        recovery_store: RecoverySnapshotStore | None = None,
        recovery_scheduler: RecoveryScheduler | None = None,
    ) -> None:
        self._presenter = presenter
        self._template_store = template_store or installation_category_template_store()
        self._document = (
            document
            if document is not None
            else new_analysis_document(template_store=self._template_store)
        )
        self._analysis_replaced = on_analysis_replaced or _do_nothing
        self._document_changed = on_document_changed or _do_nothing
        self._source_video_added = on_source_video_added or _ignore_source_video
        self._source_video_removed = on_source_video_removed or _ignore_source_video_id
        self._media_probe: MediaProbe = media_probe or FileMediaProbe()
        self._recovery_store = recovery_store or installation_recovery_store()
        self._recovery_scheduler: RecoveryScheduler = (
            recovery_scheduler or _NoRecoveryScheduling()
        )
        self._last_observed_revision = self.analysis.revision

    @property
    def document(self) -> AnalysisDocument:
        return self._document

    @property
    def analysis(self) -> Analysis:
        return self._document.analysis

    @property
    def template_store(self) -> CategoryTemplateStore:
        """Share the installation setting used when this workflow starts over."""

        return self._template_store

    @property
    def window_title(self) -> str:
        """Report the Analysis title and whether it has unsaved changes."""
        title = self.analysis.title.strip() or UNTITLED_ANALYSIS_TITLE
        marker = f"{UNSAVED_CHANGES_MARKER} " if self._document.dirty else ""
        return f"{marker}{title} — {APPLICATION_TITLE}"

    # --- Replacing the open Analysis --------------------------------------

    def may_replace_analysis(self) -> bool:
        """Decide whether the current Analysis may be let go.

        This is the single gate in front of every command that would replace or
        close the open Analysis. A cancelled prompt, a cancelled save, and a
        failed save all refuse, and all leave the Analysis document dirty.
        """
        return self._document.request_close(
            self._presenter.ask_unsaved_changes,
            self.save,
        )

    def new_analysis(self) -> bool:
        """Start an empty Analysis, seeded with the default Category template."""
        if not self.may_replace_analysis():
            return False
        self.adopt_document(new_analysis_document(template_store=self._template_store))
        return True

    def open_analysis(self) -> bool:
        """Open an Analysis file chosen from a dialog.

        The unsaved-changes decision comes first, so nobody picks a file only
        to be asked whether they meant to let their work go.
        """
        if not self.may_replace_analysis():
            return False
        chosen = self._presenter.choose_analysis_to_open()
        if not chosen:
            return False
        return self._open_decided(chosen)

    def open_analysis_file(self, path: str | Path) -> bool:
        """Open a named Analysis file, asking about unsaved changes first."""
        if not self.may_replace_analysis():
            return False
        return self._open_decided(path)

    def _open_decided(self, path: str | Path) -> bool:
        """Load a file the person has already agreed to replace their work with.

        It is decoded into a separate document, so an unreadable or rejected
        file cannot disturb the Analysis that is already open.
        """
        opened = AnalysisDocument.new()
        try:
            opened.load(path)
        except AnalysisError as error:
            self._presenter.report_failure(
                "Analysis could not be opened", str(error)
            )
            return False
        self.adopt_document(opened)
        return True

    # --- Saving ------------------------------------------------------------

    def save(self) -> bool:
        """Write the Analysis, asking for a destination when it has none.

        The external-change check runs before anything is written, so a
        conflict is caught as a question rather than as a failed or
        overwriting write.
        """
        if self._document.path is None or self._document.requires_save_as:
            return self.save_as()
        if self._document.has_external_modification():
            return self._resolve_external_change()
        return self._write(self._document.save)

    def save_as(self) -> bool:
        """Write the Analysis to a destination chosen now."""
        destination = self._presenter.choose_analysis_destination(
            self._suggested_file_name()
        )
        if not destination:
            return False
        return self._write(lambda: self._document.save_as(destination))

    def _resolve_external_change(self) -> bool:
        """Ask how to reconcile a Save with a file changed outside this app.

        Every branch either catches this document up with the other version
        or keeps this one under a new name; none of them writes over either
        file, which is the one outcome an external-change conflict must
        never produce.
        """
        choice = self._presenter.ask_external_change_conflict()
        if choice is ExternalChangeChoice.SAVE_AS:
            return self.save_as()
        if choice is ExternalChangeChoice.RELOAD:
            return self._reload_document()
        return False

    def _reload_document(self) -> bool:
        """Catch this document up with its file, discarding in-memory edits.

        Only reached once a person has chosen Reload in the external-change
        conflict, so the unsaved work it discards was always going to be the
        one thing that choice explicitly accepted losing.
        """
        try:
            self._document.reload()
        except AnalysisError as error:
            self._presenter.report_failure(
                "Analysis could not be reloaded", str(error)
            )
            return False
        self._last_observed_revision = self.analysis.revision
        self.discard_recovery()
        self._analysis_replaced()
        self._document_changed()
        return True

    def _write(self, write: Callable[[], Path]) -> bool:
        try:
            write()
        except (AnalysisError, OSError) as error:
            self._presenter.report_failure(
                "Analysis could not be saved", str(error)
            )
            return False
        self.discard_recovery()
        self._document_changed()
        return True

    def _suggested_file_name(self) -> str:
        title = self.analysis.title.strip() or _FALLBACK_ANALYSIS_FILE_NAME
        return f"{title}{ANALYSIS_FILE_SUFFIX}"

    # --- Source videos -----------------------------------------------------

    def add_source_video(self) -> SourceVideo | None:
        chosen = self._presenter.choose_source_video()
        if not chosen:
            return None
        return self.add_source_video_file(chosen)

    def add_source_video_file(self, path: str | Path) -> SourceVideo | None:
        """Add a Source video to the current Analysis without replacing it.

        The first video also titles an Analysis that has no title yet. Both
        changes are one transaction, so a rejected video leaves neither a
        Source video nor a title behind. The file is probed before the
        transaction opens, so a probe failure — a missing or unreadable path
        — is reported the same way a rejected identity is, without touching
        the Analysis at all.
        """
        if not path:
            return None
        video_path = Path(path)
        try:
            probed = self._media_probe.probe(video_path)
        except OSError as error:
            self._presenter.report_failure(
                "Source video could not be added", str(error)
            )
            return None
        analysis = self.analysis
        try:
            with analysis.transaction():
                if not analysis.title:
                    suggested_title = video_path.stem.strip()
                    if suggested_title:
                        analysis.set_title(suggested_title)
                source_video = analysis.add_or_relink_source_video(
                    video_path.name,
                    str(video_path),
                    duration_ms=probed.duration_ms,
                    byte_size=probed.byte_size,
                    fingerprint=probed.fingerprint,
                )
        except AnalysisError as error:
            self._presenter.report_failure(
                "Source video could not be added", str(error)
            )
            return None
        self._document_changed()
        self._source_video_added(source_video)
        return source_video

    def rename_source_video(self, source_video_id: UUID, display_name: str) -> bool:
        """Give a Source video an editable display name of its own."""

        try:
            self.analysis.rename_source_video(source_video_id, display_name)
        except AnalysisError as error:
            self._presenter.report_failure(
                "Source video could not be renamed", str(error)
            )
            return False
        self._document_changed()
        return True

    def reorder_source_videos(self, source_video_ids: Sequence[UUID]) -> bool:
        """Set the durable order the analyst wants Source videos to read in."""

        try:
            self.analysis.reorder_source_videos(source_video_ids)
        except AnalysisError as error:
            self._presenter.report_failure(
                "Source videos could not be reordered", str(error)
            )
            return False
        self._document_changed()
        return True

    def clip_count_for_source_video(self, source_video_id: UUID) -> int:
        """How many Clips a removal of this Source video would take with it."""

        return len(self.analysis.clips_of_source_video(source_video_id))

    def remove_source_video(self, source_video_id: UUID) -> bool:
        """Remove a Source video and every Clip that belongs to it.

        The caller is responsible for confirming a non-zero
        :meth:`clip_count_for_source_video` with the analyst first; this
        method itself always carries the cascade out, exactly as
        `Analysis.remove_source_video` defines it.
        """
        try:
            self.analysis.remove_source_video(source_video_id)
        except AnalysisError as error:
            self._presenter.report_failure(
                "Source video could not be removed", str(error)
            )
            return False
        self._document_changed()
        self._source_video_removed(source_video_id)
        return True

    def add_dropped_source_video(self, path: str | Path) -> bool:
        """Add a dropped file only when it is a supported Source video."""

        dropped = Path(path)
        if dropped.suffix.casefold() not in SOURCE_VIDEO_SUFFIXES:
            return False
        return self.add_source_video_file(dropped) is not None

    def open_dropped_file(self, path: str | Path) -> bool:
        """Handle a dropped file as the kind of file it is.

        A dropped video is added to the current Analysis; a dropped Analysis
        file replaces it. Anything else is not ours to open.
        """
        dropped = Path(path)
        suffix = dropped.suffix.casefold()
        if suffix in SOURCE_VIDEO_SUFFIXES:
            return self.add_dropped_source_video(dropped)
        if suffix == ANALYSIS_FILE_SUFFIX:
            return self.open_analysis_file(dropped)
        return False

    def adopt_document(self, document: AnalysisDocument) -> None:
        """Take over an Analysis document prepared elsewhere.

        This is the one way the open Analysis is replaced, so every route to a
        different Analysis reports the same two notifications in the same
        order. It does not ask about unsaved changes: the caller has either
        passed :meth:`may_replace_analysis` or is starting the application.
        Whatever Recovery data belonged to the Analysis being replaced is
        discarded with it — a discarded document that is not re-armed by
        :meth:`recover_if_available` right after has nothing left to recover.
        """
        self._document = document
        self._last_observed_revision = self.analysis.revision
        self.discard_recovery()
        self._analysis_replaced()
        self._document_changed()

    # --- Recovery ------------------------------------------------------------

    def note_recovery_activity(self) -> None:
        """Reschedule the debounced Recovery snapshot when content actually changed.

        Compared against the last-seen `Analysis.revision` rather than
        against whatever interface signal prompted the call, so that a
        redraw with nothing durable behind it — playback, the Active Source
        video, a selection, which sidebar tab is open — can call this freely
        without ever arming a snapshot: none of those bump the revision a
        durable content change does.
        """
        revision = self.analysis.revision
        if revision == self._last_observed_revision:
            return
        self._last_observed_revision = revision
        self._recovery_scheduler.schedule(self._write_recovery_snapshot)

    def discard_recovery(self) -> None:
        """Drop pending and stored Recovery data; it is no longer needed.

        Called after a successful save, a clean close, and a deliberate
        discard or replacement of the open Analysis — everywhere the
        in-memory Analysis is no longer at risk of being lost unrecovered.
        """
        self._recovery_scheduler.cancel()
        self._recovery_store.clear()

    def cancel_pending_recovery(self) -> None:
        """Stop a debounced Recovery write without discarding stored data.

        Unlike :meth:`discard_recovery`, this leaves whatever Recovery
        snapshot is already on disk untouched — it only stops a pending
        *write* from happening. It exists for one reason: a
        `WorkspaceViewModel` being torn down (the window closing, the object
        going out of scope in a test) must be able to silence its own
        debounce timer immediately, on its own, without deciding that the
        Analysis it was protecting no longer needs Recovery data. Deciding
        that remains `discard_recovery`'s job, reached only through an
        actual save or an accepted close.

        `RecoveryScheduler.cancel` is all the Protocol promises, and it is
        all a bare test double needs to give it: `.cancel()` alone is enough
        to stop a fake, non-Qt scheduler from ever running its pending call.
        `_TimerRecoveryScheduler` additionally offers `shutdown`, which
        latches itself permanently inert — closing the one gap `cancel`
        alone cannot, a real `QTimer.timeout` already queued on the event
        loop the instant before this runs. This is the one place that
        distinction is allowed to matter: it is checked here, next to the
        scheduler it belongs to, rather than by `WorkspaceViewModel`
        reaching past this class to decide how to tear one down.
        """
        shutdown = getattr(self._recovery_scheduler, "shutdown", None)
        if shutdown is not None:
            shutdown()
        else:
            self._recovery_scheduler.cancel()

    def _write_recovery_snapshot(self) -> None:
        try:
            self._recovery_store.write(self.analysis, self._document.path)
        except OSError:
            # A failed Recovery write must never interrupt editing; the next
            # durable change reschedules it, and a save removes the need for
            # one entirely.
            pass

    def recover_if_available(self) -> bool:
        """Offer valid Recovery data explicitly; never adopt it silently.

        A decline discards the snapshot rather than leaving it to resurface
        unexplained next time. An acceptance replaces the Analysis this
        workflow opened with, as dirty as the work it is restoring actually
        was, and immediately re-arms Recovery for it — the just-restored
        Analysis is still unsaved, and nothing will edit it again to trigger
        `note_recovery_activity` on its own.
        """
        snapshot = self._recovery_store.read()
        if snapshot is None:
            return False
        if not self._presenter.offer_recovered_analysis():
            self.discard_recovery()
            return False
        self.adopt_document(
            AnalysisDocument.recovered(snapshot.analysis, snapshot.source_path)
        )
        self._write_recovery_snapshot()
        return True


def _do_nothing() -> None:
    return None


def _ignore_source_video(source_video: SourceVideo) -> None:
    return None


def _ignore_source_video_id(source_video_id: UUID) -> None:
    return None
