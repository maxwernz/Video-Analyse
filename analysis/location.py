"""How a Source video's on-disk location is resolved without searching for it.

ADR 0003 allows exactly two attempts before a Source video is presented as
unavailable: the location recorded on it, and path information relative to
the Analysis file's own directory. The second is what lets an Analysis and
its videos, copied or moved together to another machine or folder, keep
working without any manual relinking — as long as their *relative*
arrangement survived the move, the Analysis file's new directory plus the
recorded relative path lands back on the video.

Nothing here reads bytes or opens the file as media; it only asks the
filesystem whether a path exists. Verifying that a found file is really the
expected recording — size, duration, sampled content — is `media_probe`'s
job, and only manual relinking, never this automatic resolution, needs it:
a file already sitting at one of these two predictable locations is treated
as continuity of the same Source video, not as a replacement to verify.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath


def relative_to_analysis_file(video_path: Path, analysis_path: Path | None) -> str | None:
    """A portable relative path from an Analysis file's directory to a video.

    Stored and compared as POSIX-style text — forward slashes, no drive
    letter — so an Analysis saved on Windows still resolves its videos on
    macOS and back: `pathlib.Path` accepts `/` as a separator on every
    platform this application supports, but a Windows-only backslash form
    would not mean anything on macOS. `None` means either there is nowhere
    to be relative to yet (a document with no file location) or the video
    lives on a different drive than the Analysis file, which relative path
    information cannot express.
    """
    if analysis_path is None:
        return None
    try:
        relative = video_path.resolve().relative_to(
            analysis_path.resolve().parent, walk_up=True
        )
    except ValueError:
        return None
    return relative.as_posix()


def resolve_source_video_location(
    recorded_location: str,
    relative_path: str | None,
    analysis_path: Path | None,
) -> Path | None:
    """The real path backing a Source video, trying only the two allowed spots.

    First the location last recorded for it; if that path is not there
    (moved, renamed, on a drive that is not currently attached), the
    location relative to the Analysis file's own directory — the "moved
    together" case. Neither is a filesystem search: each is exactly one
    path, checked once. Returns `None` when neither exists, which is what
    marks a Source video unavailable rather than failing the whole load.
    """
    recorded = Path(recorded_location)
    if recorded.is_file():
        return recorded
    if relative_path is not None and analysis_path is not None:
        candidate = analysis_path.resolve().parent.joinpath(
            *PurePosixPath(relative_path).parts
        )
        if candidate.is_file():
            return candidate
    return None
