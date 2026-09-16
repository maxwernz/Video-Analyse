"""Shared low-level durability primitive: write-complete, then replace.

Both :mod:`analysis.document` (an Analysis file) and :mod:`analysis.recovery`
(a Recovery snapshot) need the same guarantee — a complete temporary
representation, flushed to disk, then atomically put in place — so the
failure modes of that sequence (a failed write, a failed flush, a failed
replace, a process killed partway through) are handled in exactly one place
rather than kept in step by hand across two copies.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_replace(directory: Path, prefix: str, destination: Path, data: bytes) -> None:
    """Durably replace ``destination`` with ``data``, or leave it untouched.

    A temporary file lives beside ``destination`` only long enough to be
    written, flushed and fsynced; ``os.replace`` then puts it in place in one
    filesystem operation. Any failure along the way — including one raised
    by the caller's own encoding before this is reached — removes the
    temporary file and leaves ``destination`` exactly as it was.
    """
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=directory, prefix=prefix, suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
