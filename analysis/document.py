from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Self

from .codec import AnalysisFileCodec, AnalysisFileFormat
from .errors import (
    AnalysisError,
    AnalysisFileError,
    EmptyAnalysisError,
    LegacySourceOverwriteError,
    SaveAsRequiredError,
)
from .model import Analysis


class UnsavedChangesChoice(Enum):
    """What the user chose when asked about unsaved Analysis changes."""

    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"


class AnalysisDocument:
    """Transactional lifecycle seam for exactly one Analysis."""

    def __init__(self, analysis: Analysis, codec: AnalysisFileCodec | None = None) -> None:
        self._analysis = analysis
        self._codec = codec or AnalysisFileCodec()
        self._path: Path | None = None
        self._legacy_source_path: Path | None = None
        self._requires_save_as = False
        self._saved_revision: int | None = analysis.revision

    @classmethod
    def new(cls, title: str = "") -> Self:
        return cls(Analysis(title))

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
        decoded = self._codec.decode(data, source_path)

        self._analysis = decoded.analysis
        if decoded.file_format is AnalysisFileFormat.LEGACY_PICKLE:
            self._path = None
            self._legacy_source_path = source_path
            self._requires_save_as = True
            self._saved_revision = None
        else:
            self._path = source_path
            self._legacy_source_path = None
            self._requires_save_as = False
            self._saved_revision = self._analysis.revision

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
        destination.parent.mkdir(parents=True, exist_ok=True)
        encoded = self._codec.encode(self._analysis)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(encoded)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, destination)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
        self._saved_revision = self._analysis.revision


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
