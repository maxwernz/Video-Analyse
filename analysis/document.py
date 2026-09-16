from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Self

from ._io import atomic_replace
from .codec import AnalysisFileCodec, AnalysisFileFormat
from .errors import (
    AnalysisError,
    AnalysisFileError,
    EmptyAnalysisError,
    ExternalModificationError,
    LegacySourceOverwriteError,
    SaveAsRequiredError,
)
from .model import Analysis


class UnsavedChangesChoice(Enum):
    """What the user chose when asked about unsaved Analysis changes."""

    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"


class ExternalChangeChoice(Enum):
    """How to resolve an Analysis file that changed outside the application.

    There is no "overwrite anyway" option: a Save that finds its target
    changed on disk must never silently destroy either version, so the only
    ways forward are to catch up with the other version or to keep this
    one under a different name.
    """

    RELOAD = "reload"
    SAVE_AS = "save_as"
    CANCEL = "cancel"


#: A cheap, sufficient stand-in for "has this file changed since we looked".
#:
#: Neither field alone is reliable across every filesystem and every kind of
#: external edit; together, a mismatch in either one is real evidence the
#: file is no longer what this document last read or wrote, while re-hashing
#: the whole file on every save would cost more than the check is worth.
FileRevision = tuple[int, int]


def _file_revision(path: Path) -> FileRevision | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


class AnalysisDocument:
    """Transactional lifecycle seam for exactly one Analysis."""

    def __init__(self, analysis: Analysis, codec: AnalysisFileCodec | None = None) -> None:
        self._analysis = analysis
        self._codec = codec or AnalysisFileCodec()
        self._path: Path | None = None
        self._legacy_source_path: Path | None = None
        self._requires_save_as = False
        self._saved_revision: int | None = analysis.revision
        self._observed_revision: FileRevision | None = None

    @classmethod
    def new(cls, title: str = "") -> Self:
        return cls(Analysis(title))

    @classmethod
    def recovered(
        cls,
        analysis: Analysis,
        source_path: Path | str | None = None,
        codec: AnalysisFileCodec | None = None,
    ) -> Self:
        """Adopt Recovery-snapshot content as unsaved work.

        A Recovery snapshot is never a successful save: even though nothing
        has edited ``analysis`` since it was decoded, this document must
        still read as dirty, exactly as if an analyst had just made every
        change since the last real save by hand.

        ``source_path`` — the file the Analysis was being edited as when the
        snapshot was taken, if any — is kept rather than discarded, so the
        restored Analysis still knows which file it belongs to. It is
        deliberately *not* treated as already observed on disk: with no
        recorded revision to compare against, the first Save this document
        makes always reads as a possible external change and asks before
        overwriting, rather than assuming the file is still what it was
        before the abnormal termination.
        """
        document = cls(analysis, codec)
        document._saved_revision = None
        if source_path is not None:
            document._path = Path(source_path)
        return document

    @property
    def analysis(self) -> Analysis:
        return self._analysis

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def requires_save_as(self) -> bool:
        return self._requires_save_as

    @property
    def dirty(self) -> bool:
        return (
            self._saved_revision is None
            or self._analysis.revision != self._saved_revision
        )

    def load(self, path: str | Path) -> None:
        source_path = Path(path)
        try:
            data = source_path.read_bytes()
        except OSError as error:
            raise AnalysisFileError(
                f"Could not read Analysis file: {source_path}"
            ) from error
        # Captured immediately after the bytes actually read, rather than
        # after `decode` below: decoding a large Analysis can take long
        # enough that an external write landing during it would otherwise be
        # observed as this load's own baseline and never detected as a
        # conflict by a later save.
        observed_revision = _file_revision(source_path)
        decoded = self._codec.decode(data, source_path)

        self._analysis = decoded.analysis
        if decoded.file_format is AnalysisFileFormat.LEGACY_PICKLE:
            self._path = None
            self._legacy_source_path = source_path
            self._requires_save_as = True
            self._saved_revision = None
            self._observed_revision = None
        else:
            self._path = source_path
            self._legacy_source_path = None
            self._requires_save_as = False
            self._saved_revision = self._analysis.revision
            self._observed_revision = observed_revision

    def reload(self) -> None:
        """Reload this document's Analysis from its own file, in place.

        Reload shares :meth:`load`'s transactionality for free: `load`
        already fully reads and decodes the file into local values before
        touching ``self``, so a read failure, a malformed file, or a
        rejected schema version raises before anything already open is
        disturbed. The one thing this method adds is the precondition that
        there is a file to reload from at all.
        """
        if self._path is None:
            raise SaveAsRequiredError(
                "This Analysis has no file on disk to reload from"
            )
        self.load(self._path)

    def has_external_modification(self) -> bool:
        """Whether this document's file changed since it was loaded or saved.

        A document with no file yet, such as a brand-new or recovered
        Analysis, has nothing on disk to have diverged from.
        """
        if self._path is None:
            return False
        return _file_revision(self._path) != self._observed_revision

    def request_close(
        self,
        ask_choice: Callable[[], UnsavedChangesChoice],
        save: Callable[[], bool],
    ) -> bool:
        """Decide whether this document may close, keeping unsaved work when not.

        ``save`` reports whether the Analysis actually reached its file; a
        cancelled Save As, a failed write, or failed validation all report
        ``False`` and keep the document open with its unsaved state intact.
        """
        if not self.dirty:
            return True
        choice = ask_choice()
        if choice is UnsavedChangesChoice.CANCEL:
            return False
        if choice is UnsavedChangesChoice.DISCARD:
            return True
        try:
            return bool(save())
        except AnalysisError:
            return False

    def save(self) -> Path:
        if self._path is None or self._requires_save_as:
            raise SaveAsRequiredError(
                "This Analysis must be saved with Save As before it can be saved"
            )
        if self.has_external_modification():
            raise ExternalModificationError(
                f"Analysis file changed on disk since it was opened: {self._path}"
            )
        self._write_current_analysis(self._path)
        return self._path

    def save_as(self, path: str | Path) -> Path:
        destination = _analysis_path(Path(path))
        if (
            self._legacy_source_path is not None
            and _same_file(destination, self._legacy_source_path)
        ):
            raise LegacySourceOverwriteError(
                "Save As cannot overwrite the original legacy Analysis file"
            )
        self._write_current_analysis(destination)
        self._path = destination
        self._legacy_source_path = None
        self._requires_save_as = False
        return destination

    def _write_current_analysis(self, destination: Path) -> None:
        if not self._analysis.source_videos:
            raise EmptyAnalysisError(
                "An Analysis needs at least one Source video before it can be saved"
            )
        encoded = self._codec.encode(self._analysis)
        atomic_replace(
            destination.parent, f".{destination.name}.", destination, encoded
        )
        self._saved_revision = self._analysis.revision
        self._observed_revision = _file_revision(destination)


def _analysis_path(path: Path) -> Path:
    if path.suffix == ".analysis":
        return path
    if path.suffix.casefold() == ".analysis":
        return path.with_suffix(".analysis")
    return path.with_name(path.name + ".analysis")


def _same_file(first: Path, second: Path) -> bool:
    try:
        return first.samefile(second)
    except OSError:
        return first.resolve() == second.resolve()
