"""How a Source video's identity is measured from its bytes.

The parent Analysis spec (`#12`) decided that normal identity verification
never needs a full-file hash: a digest of a few stable regions, combined with
byte size and duration, is stable enough to tell one physical recording from
another while staying effectively instant on a multi-gigabyte file. This
module is where that sampling lives, kept independent of `analysis/` because
it reads real files rather than deciding what an Analysis is.

`ApplicationWorkflow` takes a `MediaProbe` as a dependency rather than calling
a probe directly, so its tests can supply `FakeMediaProbe` and assert
duplicate-rejection and relink behaviour without touching real media — the
same seam the parent issue asked for alongside the fake player.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

#: Bytes read at each sampled offset. Large enough that a rewritten header a
#: few kilobytes long cannot flip the fingerprint by accident, small enough
#: that probing a multi-gigabyte recording stays effectively instant.
SAMPLE_SIZE = 65_536

#: Where within the file each sample is taken, as a fraction of its length.
#: Fixed, stable regions rather than a full read — a file's beginning,
#: middle and end are exactly the regions least likely to be rewritten by a
#: player, a container remux, or a filesystem copy.
SAMPLE_OFFSETS = (0.0, 0.5, 1.0)


@dataclass(frozen=True, slots=True)
class ProbedMedia:
    """What was learned about a Source video's file without a full-file hash."""

    byte_size: int
    fingerprint: str
    duration_ms: int | None


class MediaProbe(Protocol):
    """A pluggable way to measure a Source video before it joins an Analysis."""

    def probe(self, path: Path) -> ProbedMedia: ...


class FileMediaProbe:
    """Probes a Source video from its bytes, sampled rather than hashed whole.

    Duration alone needs a real decode, so it is read through moviepy —
    already a dependency for Combined export — and is left `None` when the
    file cannot be opened as media. Byte size and the fingerprint never
    depend on a successful decode, so a video whose duration probe fails can
    still be added, and a later relink attempt can still recognize it once
    duration becomes known.
    """

    def probe(self, path: Path) -> ProbedMedia:
        byte_size = path.stat().st_size
        return ProbedMedia(
            byte_size=byte_size,
            fingerprint=_sample_fingerprint(path, byte_size),
            duration_ms=_probe_duration_ms(path),
        )


def _sample_fingerprint(path: Path, byte_size: int) -> str:
    digest = hashlib.sha256()
    digest.update(str(byte_size).encode("ascii"))
    with path.open("rb") as media_file:
        for fraction in SAMPLE_OFFSETS:
            offset = min(int(byte_size * fraction), max(byte_size - SAMPLE_SIZE, 0))
            media_file.seek(offset)
            digest.update(media_file.read(SAMPLE_SIZE))
    return digest.hexdigest()


def _probe_duration_ms(path: Path) -> int | None:
    try:
        from moviepy.editor import VideoFileClip
    except Exception:  # pragma: no cover - moviepy is a hard dependency here
        return None
    clip = None
    try:
        clip = VideoFileClip(str(path))
        return int(clip.duration * 1000)
    except Exception:
        # Not every file added to an Analysis need be one moviepy can open
        # immediately; a missing duration is resolved later rather than
        # blocking the add.
        return None
    finally:
        if clip is not None:
            clip.close()
