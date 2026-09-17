"""The application workflow layer over one Analysis document.

This module owns the document commands — New, Open, Save, Save As, and Close —
the unsaved-changes decision flow, and additive Source-video adding. It reports
the window title, so the interface above it renders a decision rather than
making one.

It deliberately holds no user-interface types. Everything it needs from a person
arrives through a :class:`WorkflowPresenter`, and everything the interface needs
to redraw arrives as one of three notifications, which keeps the whole layer
testable without widgets, dialogs, or media.

Every command that can ask a person something is **continuation-based**: it
takes an ``on_done`` completion instead of returning a value, and calls it
exactly once, whenever the whole command has settled. This is not a style
preference. Issue #69 found that every synchronous, `exec()`'d Qt dialog —
`QFileDialog` and `QMessageBox` alike — can self-cancel in under a second
purely from OS-level hover-tracking state, with no reliable workaround. The
one dialog that survives, `QtQuick.Dialogs.FileDialog`, is asynchronous by
construction, so a presenter backed by it cannot answer a question on the
same call stack that asked it. Every command downstream of a question a
person might be asked has to be asynchronous too, all the way up to
`WorkspaceViewModel` and `menu_bar`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TypeVar
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

_Answer = TypeVar("_Answer")


class WorkflowPresenter(Protocol):
    """Every decision the workflow asks a person to make, and every report.

    A chooser calls its completion with ``None`` when the person dismissed
    the dialog, which the workflow treats as cancelling the command rather
    than as a failure. Every method here returns immediately — the answer,
    when there is one, arrives later through ``on_result`` — because the one
    dialog technology issue #69 found immune to Qt/Cocoa's hover-tracking
    self-cancel (`QtQuick.Dialogs.FileDialog`) is itself asynchronous.
    `report_failure` is the one exception: nothing downstream of it needs to
    know when the analyst has dismissed a notice, so it stays fire-and-forget.
    """

    def ask_unsaved_changes(
        self, on_result: Callable[[UnsavedChangesChoice], None]
    ) -> None:
        """Ask what should happen to unsaved Analysis changes."""

    def ask_external_change_conflict(
        self, on_result: Callable[[ExternalChangeChoice], None]
    ) -> None:
        """Ask how to resolve an Analysis file changed outside the application."""

    def offer_recovered_analysis(self, on_result: Callable[[bool], None]) -> None:
        """Ask whether to restore Recovery data found after abnormal termination.

        Calling ``on_result`` with ``False`` — including a dismissed prompt —
        is read as declining it, which discards the offered snapshot rather
        than leaving it to be offered again unexplained next time.
        """

    def choose_analysis_to_open(
        self, on_result: Callable[[str | None], None]
    ) -> None:
        """Ask which Analysis file to open."""

    def choose_analysis_destination(
        self, suggested_name: str, on_result: Callable[[str | None], None]
    ) -> None:
        """Ask where to write the Analysis file."""

    def choose_source_video(self, on_result: Callable[[str | None], None]) -> None:
        """Ask which video file to add as a Source video."""

    def choose_replacement_media(
        self, display_name: str, on_result: Callable[[str | None], None]
    ) -> None:
        """Ask which media file should relink an unavailable Source video."""

    def confirm_source_video_replacement(
        self, display_name: str, on_result: Callable[[bool], None]
    ) -> None:
        """Ask whether to adopt media whose identity does not verify.

        Only reached when the chosen file's size, duration, and sampled
        fingerprint do not all match what is on record for this Source
        video — a verified match relinks without asking. Calling
        ``on_result`` with ``False``, like a dismissed dialog, is read as
        no: the Source video stays exactly as unavailable as it was.
        """

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


def _ignore_bool(_result: bool) -> None:
    return None


def _ignore_source_video(_result: SourceVideo | None) -> None:
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
        self._source_video_added = on_source_video_added or _ignore_source_video_added
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

    def _still_current(self, document: AnalysisDocument) -> bool:
        """Whether ``document`` is still the Analysis a command started against.

        A continuation captured before an asynchronous dialog round-trips
        can only see the document that is open *now* — attribute lookup on
        `self._document` happens when the dialog answers, not when the
        command began. Between the dialog opening and its answer arriving,
        `may_replace_analysis` can swap `self._document` with **no dialog of
        its own**: a New command against a not-dirty document decides
        instantly, so it slips through the one guard
        (`WorkspacePresenter`'s pending-callback check) that would otherwise
        serialise commands, because that guard only serialises *new dialog
        requests*, not swaps that need no dialog at all. That is exactly the
        gap issue #69's own diagnosis found the parentless macOS menu bar
        reaches through while a sheet is open.

        Every command that resumes after an awaited dialog and is about to
        act on the document it started with — write to it, mutate it, read
        it to build a write — calls this first and settles as not-done
        rather than acting on whichever document happens to be open when
        the answer arrives. Identity (``is``), not equality: a swapped-in
        document that happens to describe the same Analysis, or even carry
        the same Source-video id (a Recovery restore of the same file, for
        instance), is still the wrong target once the one this command
        started against has been let go.
        """

        return document is self._document

    def _guard(
        self,
        document: AnalysisDocument,
        after: Callable[[_Answer], None],
        on_stale: Callable[[], None],
    ) -> Callable[[_Answer], None]:
        """Wrap a dialog completion so it only runs if ``document`` is still open.

        Every dialog-backed command hands this to the presenter instead of
        its raw continuation, at the one place it hands control to
        something that can await a person. That is the one place the
        capture-and-check in :meth:`_still_current` has to happen — folding
        it in here means a new command cannot add a dialog and forget the
        check, the way the bug this guards against was written the first
        time. ``on_stale`` decides what "not done" means for that
        particular command: a write settles quietly as not-done, while a
        command that would otherwise discard the document now open —
        Open, and an accepted Recovery offer — reports why nothing
        happened, because the analyst asked for something explicit and
        silence would look like nothing had gone wrong.
        """

        def guarded(value: _Answer) -> None:
            if not self._still_current(document):
                on_stale()
                return
            after(value)

        return guarded

    def _abandon_open(self, on_done: Callable[[bool], None]) -> None:
        """Refuse an Open whose document changed while its dialog was pending.

        Reached only when the Analysis this Open started against was
        replaced — by another New, another Open, or an accepted Recovery
        offer, none of which need a dialog of their own to do it — while
        this command was still waiting on `may_replace_analysis` or on the
        file chooser. Discarding whatever is open now to honour a stale
        Open would be exactly the bug this module's guard exists to
        prevent; reporting instead of settling silently is because the
        analyst explicitly asked to open something, and deserves to know
        it did not happen rather than see nothing.
        """

        self._presenter.report_failure(
            "Analysis could not be opened",
            "The open Analysis changed while this question was pending.",
        )
        on_done(False)

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

    def may_replace_analysis(self, on_done: Callable[[bool], None]) -> None:
        """Decide whether the current Analysis may be let go.

        This is the single gate in front of every command that would replace or
        close the open Analysis. A cancelled prompt, a cancelled save, and a
        failed save all refuse, and all leave the Analysis document dirty.

        This used to delegate straight to `AnalysisDocument.request_close`,
        which is still there and still covers the same three-way decision —
        it is exercised on its own in `tests/test_analysis_close.py`. It
        cannot be reused here: it takes plain callables and returns a plain
        `bool`, and both of those became untellable from a real answer the
        moment `ask_unsaved_changes` stopped answering on the same call
        stack that asked it. This is the same decision, written out as the
        explicit continuation `request_close` cannot express: not dirty
        decides itself; Cancel and Discard settle immediately; Save chains
        into `save`, whose own outcome — including a cancelled Save As
        nested inside it — is what finally decides this.
        """

        if not self._document.dirty:
            on_done(True)
            return

        def after_choice(choice: UnsavedChangesChoice) -> None:
            if choice is UnsavedChangesChoice.DISCARD:
                on_done(True)
            elif choice is UnsavedChangesChoice.SAVE:
                self.save(on_done)
            else:
                on_done(False)

        self._presenter.ask_unsaved_changes(after_choice)

    def new_analysis(self, on_done: Callable[[bool], None] = _ignore_bool) -> None:
        """Start an empty Analysis, seeded with the default Category template.

        The document is captured before `may_replace_analysis` asks
        anything: its own unsaved-changes question, or a Save it chains
        into, can take long enough for a different command — another New,
        another Open, an accepted Recovery offer — to replace
        `self._document` first, with no dialog of its own (see
        :meth:`_still_current`). Acting on `may_replace_analysis`'s answer
        against a document it was never asked about would repeat the same
        mistake this module's guard exists to prevent, so a stale answer
        here simply settles as not-done: nothing was explicitly chosen, so
        unlike Open there is nothing to report failing.
        """

        document = self._document

        def after_replace(may_replace: bool) -> None:
            if not may_replace:
                on_done(False)
                return
            self.adopt_document(
                new_analysis_document(template_store=self._template_store)
            )
            on_done(True)

        self.may_replace_analysis(
            self._guard(document, after_replace, lambda: on_done(False))
        )

    def open_analysis(self, on_done: Callable[[bool], None] = _ignore_bool) -> None:
        """Open an Analysis file chosen from a dialog.

        The unsaved-changes decision comes first, so nobody picks a file only
        to be asked whether they meant to let their work go. The document is
        captured once, before that first question, and the same snapshot
        guards both it and the file chooser after it: by the time the first
        guard has let `after_replace` run, `document` is confirmed current,
        so the second guard is checking against the same, still-valid
        reference rather than needing a fresh one (see :meth:`_still_current`).
        A stale answer at either gap reports through :meth:`_abandon_open`,
        since here — unlike New — the analyst did explicitly ask to open
        something.
        """

        document = self._document

        def after_replace(may_replace: bool) -> None:
            if not may_replace:
                on_done(False)
                return

            def after_choice(chosen: str | None) -> None:
                if not chosen:
                    on_done(False)
                    return
                self._open_decided(chosen, on_done)

            self._presenter.choose_analysis_to_open(
                self._guard(document, after_choice, lambda: self._abandon_open(on_done))
            )

        self.may_replace_analysis(
            self._guard(document, after_replace, lambda: self._abandon_open(on_done))
        )

    def open_analysis_file(
        self, path: str | Path, on_done: Callable[[bool], None] = _ignore_bool
    ) -> None:
        """Open a named Analysis file, asking about unsaved changes first.

        A specific file was already named, so a document swapped in while
        `may_replace_analysis` was pending is guarded the same way
        `open_analysis` guards its own first gap — reported through
        :meth:`_abandon_open` rather than settled silently.
        """

        document = self._document

        def after_replace(may_replace: bool) -> None:
            if not may_replace:
                on_done(False)
                return
            self._open_decided(path, on_done)

        self.may_replace_analysis(
            self._guard(document, after_replace, lambda: self._abandon_open(on_done))
        )

    def _open_decided(
        self, path: str | Path, on_done: Callable[[bool], None]
    ) -> None:
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
            on_done(False)
            return
        self.adopt_document(opened)
        on_done(True)

    # --- Saving ------------------------------------------------------------

    def save(self, on_done: Callable[[bool], None] = _ignore_bool) -> None:
        """Write the Analysis, asking for a destination when it has none.

        The external-change check runs before anything is written, so a
        conflict is caught as a question rather than as a failed or
        overwriting write.
        """
        if self._document.path is None or self._document.requires_save_as:
            self.save_as(on_done)
            return
        if self._document.has_external_modification():
            self._resolve_external_change(on_done)
            return
        self._write(self._document.save, on_done)

    def save_as(self, on_done: Callable[[bool], None] = _ignore_bool) -> None:
        """Write the Analysis to a destination chosen now.

        The document is captured before the destination dialog opens and
        guarded through :meth:`_guard`: see that method, and
        :meth:`_still_current`, for why a plain `self._document` read in
        `after_destination` would be reading whatever document is open
        when the dialog closes, not the one Save As was actually invoked
        for.
        """

        document = self._document

        def after_destination(destination: str | None) -> None:
            if not destination:
                on_done(False)
                return
            self._write(lambda: document.save_as(destination), on_done)

        self._presenter.choose_analysis_destination(
            self._suggested_file_name(),
            self._guard(document, after_destination, lambda: on_done(False)),
        )

    def _resolve_external_change(self, on_done: Callable[[bool], None]) -> None:
        """Ask how to reconcile a Save with a file changed outside this app.

        Every branch either catches this document up with the other version
        or keeps this one under a new name; none of them writes over either
        file, which is the one outcome an external-change conflict must
        never produce.

        The document is captured before the question opens: both the
        Save As and the Reload branch below would otherwise act on whatever
        is open when the question is answered rather than the document
        this Save actually started against (see :meth:`_still_current`).
        Save As is guarded again, independently, inside :meth:`save_as`
        itself — it has its own dialog and its own gap — so this guard
        only has to cover Reload and the moment the choice arrives.
        """

        document = self._document

        def after_choice(choice: ExternalChangeChoice) -> None:
            if choice is ExternalChangeChoice.SAVE_AS:
                self.save_as(on_done)
            elif choice is ExternalChangeChoice.RELOAD:
                on_done(self._reload_document())
            else:
                on_done(False)

        self._presenter.ask_external_change_conflict(
            self._guard(document, after_choice, lambda: on_done(False))
        )

    def _reload_document(self) -> bool:
        """Catch this document up with its file, discarding in-memory edits.

        Only reached once a person has chosen Reload in the external-change
        conflict, so the unsaved work it discards was always going to be the
        one thing that choice explicitly accepted losing. Nothing here asks
        a person anything, so it stays synchronous.
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

    def _write(
        self, write: Callable[[], Path], on_done: Callable[[bool], None]
    ) -> None:
        try:
            write()
        except (AnalysisError, OSError) as error:
            self._presenter.report_failure(
                "Analysis could not be saved", str(error)
            )
            on_done(False)
            return
        self.discard_recovery()
        self._document_changed()
        on_done(True)

    def _suggested_file_name(self) -> str:
        title = self.analysis.title.strip() or _FALLBACK_ANALYSIS_FILE_NAME
        return f"{title}{ANALYSIS_FILE_SUFFIX}"

    # --- Source videos -----------------------------------------------------

    def add_source_video(
        self,
        on_done: Callable[[SourceVideo | None], None] = _ignore_source_video,
    ) -> None:
        """Ask which Source video to add to the Analysis open right now.

        The document is captured before the file dialog opens, so a New or
        Open that swaps `self._document` while the dialog is pending (see
        :meth:`_still_current`) is not silently absorbed into whatever
        Analysis happens to be open when a file is finally chosen.
        """

        document = self._document

        def after_choice(chosen: str | None) -> None:
            if not chosen:
                on_done(None)
                return
            on_done(self.add_source_video_file(chosen))

        self._presenter.choose_source_video(
            self._guard(document, after_choice, lambda: on_done(None))
        )

    def add_source_video_file(self, path: str | Path) -> SourceVideo | None:
        """Add a Source video to the current Analysis without replacing it.

        The first video also titles an Analysis that has no title yet. Both
        changes are one transaction, so a rejected video leaves neither a
        Source video nor a title behind. The file is probed before the
        transaction opens, so a probe failure — a missing or unreadable path
        — is reported the same way a rejected identity is, without touching
        the Analysis at all. Nothing here asks a person anything, so this
        stays synchronous; `add_source_video` is the continuation-based
        entry point in front of it that does.
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
        relative_path = self._document.relative_source_video_path(video_path)
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
                    relative_path=relative_path,
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

    def is_source_video_available(self, source_video_id: UUID) -> bool:
        """Whether this Source video currently resolves to real media.

        Backed entirely by :meth:`AnalysisDocument.resolve_source_video`, so
        it tries only the recorded location and the location relative to the
        Analysis file — never an arbitrary search — and mutates nothing.
        """
        return self._document.is_source_video_available(source_video_id)

    def relink_source_video(
        self,
        source_video_id: UUID,
        on_done: Callable[[bool], None] = _ignore_bool,
    ) -> None:
        """Ask for replacement media and relink it to an unavailable Source video.

        The document is captured before the file dialog opens (see
        :meth:`_still_current`): a document swapped in while the analyst is
        still choosing a file could coincidentally hold a Source video with
        the same id — a Recovery restore of the same file, say — so a
        UUID-only re-lookup inside `relink_source_video_file` cannot be
        trusted alone to catch a mid-flight swap.
        """

        try:
            source_video = self.analysis.source_video(source_video_id)
        except AnalysisError as error:
            self._presenter.report_failure(
                "Source video could not be relinked", str(error)
            )
            on_done(False)
            return

        document = self._document

        def after_choice(chosen: str | None) -> None:
            if not chosen:
                on_done(False)
                return
            self.relink_source_video_file(source_video_id, chosen, on_done)

        self._presenter.choose_replacement_media(
            source_video.display_name,
            self._guard(document, after_choice, lambda: on_done(False)),
        )

    def relink_source_video_file(
        self,
        source_video_id: UUID,
        path: str | Path,
        on_done: Callable[[bool], None] = _ignore_bool,
    ) -> None:
        """Point a Source video at replacement media, verifying its identity first.

        Size, duration, and sampled fingerprint all matching what is already
        on record relinks immediately and keeps every existing Clip exactly
        as it was — the same silent continuity `add_or_relink_source_video`
        gives a moved video found again by normal adding. Anything else,
        including a Source video that was never probed to begin with, is a
        real replacement question and needs the analyst's explicit
        confirmation, which warns that existing Clip timestamps may no
        longer describe this new media. A probe failure, an unknown Source
        video, a declined confirmation, or a rejected domain change all
        leave the Source video exactly as unavailable as it was — nothing
        here writes to the Analysis until identity is settled one way or
        the other.

        The document open when this method was entered is captured once and
        used throughout, and the confirmation question — the unverified
        branch's own dialog gap — is guarded through :meth:`_guard` exactly
        as the file dialog in `relink_source_video` is, so a document swap
        while that confirmation is pending cannot reach `proceed`'s write
        (see :meth:`_still_current`).
        """
        if not path:
            on_done(False)
            return
        document = self._document
        video_path = Path(path)
        try:
            probed = self._media_probe.probe(video_path)
        except OSError as error:
            self._presenter.report_failure(
                "Replacement media could not be read", str(error)
            )
            on_done(False)
            return
        try:
            existing = document.analysis.source_video(source_video_id)
        except AnalysisError as error:
            self._presenter.report_failure(
                "Source video could not be relinked", str(error)
            )
            on_done(False)
            return
        verified = (
            existing.byte_size is not None
            and existing.duration_ms is not None
            and existing.fingerprint is not None
            and existing.byte_size == probed.byte_size
            and existing.duration_ms == probed.duration_ms
            and existing.fingerprint == probed.fingerprint
        )

        def proceed() -> None:
            relative_path = document.relative_source_video_path(video_path)
            try:
                document.analysis.relink_source_video(
                    source_video_id,
                    str(video_path),
                    relative_path=relative_path,
                    duration_ms=probed.duration_ms,
                    byte_size=probed.byte_size,
                    fingerprint=probed.fingerprint,
                )
            except AnalysisError as error:
                self._presenter.report_failure(
                    "Source video could not be relinked", str(error)
                )
                on_done(False)
                return
            self._document_changed()
            on_done(True)

        if verified:
            proceed()
            return

        def after_confirm(confirmed: bool) -> None:
            if not confirmed:
                on_done(False)
                return
            proceed()

        self._presenter.confirm_source_video_replacement(
            existing.display_name,
            self._guard(document, after_confirm, lambda: on_done(False)),
        )

    def add_dropped_source_video(self, path: str | Path) -> bool:
        """Add a dropped file only when it is a supported Source video.

        Adding a dropped video never asks a person anything — it goes
        straight to `add_source_video_file`, not through the dialog-backed
        `add_source_video` — so this stays synchronous.
        """

        dropped = Path(path)
        if dropped.suffix.casefold() not in SOURCE_VIDEO_SUFFIXES:
            return False
        return self.add_source_video_file(dropped) is not None

    def open_dropped_file(
        self, path: str | Path, on_done: Callable[[bool], None] = _ignore_bool
    ) -> None:
        """Handle a dropped file as the kind of file it is.

        A dropped video is added to the current Analysis; a dropped Analysis
        file replaces it. Anything else is not ours to open. Only the second
        branch can ask a person anything — replacing the open Analysis may
        need the unsaved-changes question — so this is continuation-based
        even though the video branch always settles before returning.
        """
        dropped = Path(path)
        suffix = dropped.suffix.casefold()
        if suffix in SOURCE_VIDEO_SUFFIXES:
            on_done(self.add_dropped_source_video(dropped))
            return
        if suffix == ANALYSIS_FILE_SUFFIX:
            self.open_analysis_file(dropped, on_done)
            return
        on_done(False)

    def adopt_document(self, document: AnalysisDocument) -> None:
        """Take over an Analysis document prepared elsewhere.

        This is the one way the open Analysis is replaced, so every route to a
        different Analysis reports the same two notifications in the same
        order. It does not ask about unsaved changes: the caller has either
        settled :meth:`may_replace_analysis` or is starting the application.
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

    def _write_recovery_snapshot(self) -> None:
        try:
            self._recovery_store.write(self.analysis, self._document.path)
        except OSError:
            # A failed Recovery write must never interrupt editing; the next
            # durable change reschedules it, and a save removes the need for
            # one entirely.
            pass

    def recover_if_available(
        self, on_done: Callable[[bool], None] = _ignore_bool
    ) -> None:
        """Offer valid Recovery data explicitly; never adopt it silently.

        A decline discards the snapshot rather than leaving it to resurface
        unexplained next time. An acceptance replaces the Analysis this
        workflow opened with, as dirty as the work it is restoring actually
        was, and immediately re-arms Recovery for it — the just-restored
        Analysis is still unsaved, and nothing will edit it again to trigger
        `note_recovery_activity` on its own.

        `main.py` shows this offer and builds the native menu bar in the
        same breath, so the Analysis this offer was raised against can be
        replaced — by a menu New, another Open, anything that reaches
        `adopt_document` — before the analyst has answered. Accepting a
        stale offer would discard whatever is open now exactly as
        `_open_decided` almost did; the document is captured and guarded
        the same way (see :meth:`_still_current`). This guard's own stale
        branch never discards the snapshot on a late accept — only a real
        decline does — though whatever replaced the document in the
        meantime will typically have discarded it anyway, every present
        route there being `adopt_document` itself; the distinction still
        matters if a future replacement route ever is not.
        """
        snapshot = self._recovery_store.read()
        if snapshot is None:
            on_done(False)
            return

        document = self._document

        def after_offer(accepted: bool) -> None:
            if not accepted:
                self.discard_recovery()
                on_done(False)
                return
            self.adopt_document(
                AnalysisDocument.recovered(snapshot.analysis, snapshot.source_path)
            )
            self._write_recovery_snapshot()
            on_done(True)

        def on_stale() -> None:
            self._presenter.report_failure(
                "Recovered Analysis could not be restored",
                "The open Analysis changed while this question was pending.",
            )
            on_done(False)

        self._presenter.offer_recovered_analysis(
            self._guard(document, after_offer, on_stale)
        )


def _do_nothing() -> None:
    return None


def _ignore_source_video_added(source_video: SourceVideo) -> None:
    return None


def _ignore_source_video_id(source_video_id: UUID) -> None:
    return None
