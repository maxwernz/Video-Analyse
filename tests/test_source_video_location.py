"""How a Source video's on-disk location is resolved, and only ever those two ways.

`analysis.location` is the pure seam ADR 0003 describes: try the recorded
location, then try path information relative to the Analysis file, and never
search a filesystem tree. These tests exercise it directly with real
temporary files, plus the portable relative-path text it produces, in forms
that must round-trip whether the Analysis was last saved on Windows or macOS.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

from analysis.location import relative_to_analysis_file, resolve_source_video_location


# --- relative_to_analysis_file ---------------------------------------------


def test_a_video_beside_the_analysis_file_gets_a_bare_relative_path(
    tmp_path: Path,
) -> None:
    analysis_path = tmp_path / "match.analysis"
    video_path = tmp_path / "first-half.mp4"

    assert relative_to_analysis_file(video_path, analysis_path) == "first-half.mp4"


def test_a_video_in_a_subfolder_gets_a_forward_slash_relative_path(
    tmp_path: Path,
) -> None:
    analysis_path = tmp_path / "match.analysis"
    video_path = tmp_path / "videos" / "first-half.mp4"

    assert (
        relative_to_analysis_file(video_path, analysis_path) == "videos/first-half.mp4"
    )


def test_a_video_in_a_sibling_folder_gets_a_walk_up_relative_path(
    tmp_path: Path,
) -> None:
    analysis_directory = tmp_path / "analyses"
    analysis_directory.mkdir()
    analysis_path = analysis_directory / "match.analysis"
    video_path = tmp_path / "videos" / "first-half.mp4"

    assert (
        relative_to_analysis_file(video_path, analysis_path)
        == "../videos/first-half.mp4"
    )


def test_no_analysis_path_means_no_relative_path_yet(tmp_path: Path) -> None:
    assert relative_to_analysis_file(tmp_path / "first-half.mp4", None) is None


# --- resolve_source_video_location ------------------------------------------


def test_a_video_at_its_recorded_location_resolves_there(tmp_path: Path) -> None:
    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(b"video")

    resolved = resolve_source_video_location(str(video_path), None, None)

    assert resolved == video_path


def test_a_missing_recorded_location_with_no_relative_path_is_unavailable(
    tmp_path: Path,
) -> None:
    resolved = resolve_source_video_location(
        str(tmp_path / "gone.mp4"), None, tmp_path / "match.analysis"
    )

    assert resolved is None


def test_moved_together_resolves_through_the_relative_path(tmp_path: Path) -> None:
    """The Analysis and its video moved to a new folder, together.

    The recorded location — wherever it used to be — no longer exists, but
    the relative arrangement between the Analysis file and its video
    survived the move, so this is exactly the case ADR 0003 asks resolution
    to recover without a filesystem search.
    """

    new_directory = tmp_path / "moved"
    videos_directory = new_directory / "videos"
    videos_directory.mkdir(parents=True)
    video_path = videos_directory / "first-half.mp4"
    video_path.write_bytes(b"video")
    analysis_path = new_directory / "match.analysis"

    resolved = resolve_source_video_location(
        "/old/location/first-half.mp4",
        "videos/first-half.mp4",
        analysis_path,
    )

    assert resolved == video_path


def test_relative_resolution_never_searches_beyond_the_one_named_path(
    tmp_path: Path,
) -> None:
    """A same-named file elsewhere must not be found by a broader search."""

    decoy_directory = tmp_path / "decoy"
    decoy_directory.mkdir()
    (decoy_directory / "first-half.mp4").write_bytes(b"decoy")
    analysis_directory = tmp_path / "real"
    analysis_directory.mkdir()
    analysis_path = analysis_directory / "match.analysis"

    resolved = resolve_source_video_location(
        "/old/location/first-half.mp4",
        "videos/first-half.mp4",
        analysis_path,
    )

    assert resolved is None


def test_a_windows_style_recorded_location_is_unavailable_on_this_platform_but_relinks_relatively(
    tmp_path: Path,
) -> None:
    """An Analysis saved on Windows still resolves its video on this platform.

    The recorded location is a Windows path that cannot exist here; only
    the portable, forward-slash relative path — the form this module always
    stores and reads — is expected to still find the file.
    """

    video_path = tmp_path / "videos" / "first-half.mp4"
    video_path.parent.mkdir()
    video_path.write_bytes(b"video")
    analysis_path = tmp_path / "match.analysis"
    windows_recorded_location = str(PureWindowsPath(r"C:\Users\Coach\Videos\first-half.mp4"))

    resolved = resolve_source_video_location(
        windows_recorded_location, "videos/first-half.mp4", analysis_path
    )

    assert resolved == video_path
