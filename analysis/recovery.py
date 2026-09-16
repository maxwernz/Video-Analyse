"""Separately stored, temporary representation of unsaved Analysis changes.

A Recovery snapshot exists for exactly one reason: to give an analyst back
work an abnormal termination would otherwise lose. It is deliberately never
part of the Analysis file lifecycle in :mod:`analysis.document` — it lives
under its own installation-local location (resolved through
``category_template_settings``'s ``QStandardPaths`` precedent, from
:mod:`recovery_settings`), under a name and an explicit marker no
`AnalysisDocument.load` path recognizes as a real file. It can therefore
never be opened by File > Open, and reading it back can never be mistaken
for a successful save.

The stored bytes still borrow :class:`~analysis.codec.AnalysisFileCodec`'s
own JSON shape for the Analysis it wraps, rather than inventing a second
serialization to keep in step with `Analysis`'s fields by hand.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from ._io import atomic_replace
from .codec import AnalysisFileCodec
from .errors import AnalysisError
from .model import Analysis

#: Marks a stored JSON document as Recovery data rather than an Analysis file.
RECOVERY_MARKER = "recovery_snapshot"

#: Deliberately unlike any user-chosen Analysis file name, and without the
#: ``.analysis`` suffix a file dialog filters on.
RECOVERY_FILE_NAME = "unsaved-analysis.recovery.json"


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    """Recovery data read back, before an analyst has decided to restore it."""

    analysis: Analysis
    source_path: Path | None
    recorded_at: float


class RecoverySnapshotStore:
    """Installation-local durable storage for one unsaved Analysis snapshot.

    Exactly one Analysis is ever open at a time, so one location is enough:
    a later snapshot durably replaces whatever the earlier one recorded, the
    same way `AnalysisDocument` durably replaces one Analysis file.
    """

    def __init__(self, directory: Path, codec: AnalysisFileCodec | None = None) -> None:
        self._directory = directory
        self._path = directory / RECOVERY_FILE_NAME
        self._codec = codec or AnalysisFileCodec()

    @property
    def path(self) -> Path:
        return self._path

    def write(self, analysis: Analysis, source_path: Path | None) -> None:
        """Durably replace the stored snapshot with this Analysis's content.

        Written the same way an Analysis file is: a complete temporary
        representation, flushed, then atomically put in place, so a snapshot
        interrupted mid-write never leaves a half-written file behind — an
        analyst would only ever be offered the previous complete snapshot,
        or none at all if there had not been one yet.
        """
        envelope = self._codec.to_payload(analysis)
        envelope[RECOVERY_MARKER] = True
        envelope["source_path"] = str(source_path) if source_path is not None else None
        envelope["recorded_at"] = time.time()
        data = (
            json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        atomic_replace(
            self._directory, f".{RECOVERY_FILE_NAME}.", self._path, data
        )

    def read(self) -> RecoverySnapshot | None:
        """Return valid Recovery data, or ``None`` when there is nothing to offer.

        Content that is missing, unreadable, foreign, or fails to decode as
        a valid Analysis is treated exactly like no snapshot existing,
        rather than surfaced as a confusing failure over content nobody
        asked to open. A stale or corrupt snapshot must never block startup.
        """
        try:
            data = self._path.read_bytes()
        except OSError:
            return None
        try:
            payload = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get(RECOVERY_MARKER) is not True:
            return None
        try:
            decoded = self._codec.decode(data, self._path)
        except AnalysisError:
            return None
        source_path_value = payload.get("source_path")
        source_path = (
            Path(source_path_value) if isinstance(source_path_value, str) else None
        )
        recorded_at_value = payload.get("recorded_at")
        recorded_at = (
            float(recorded_at_value)
            if isinstance(recorded_at_value, (int, float))
            and not isinstance(recorded_at_value, bool)
            else 0.0
        )
        return RecoverySnapshot(
            analysis=decoded.analysis,
            source_path=source_path,
            recorded_at=recorded_at,
        )

    def clear(self) -> None:
        """Remove obsolete Recovery data; never an error when there is none."""
        self._path.unlink(missing_ok=True)
