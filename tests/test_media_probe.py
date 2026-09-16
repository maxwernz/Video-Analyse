"""How a Source video's identity is sampled from its bytes.

`FileMediaProbe` is the default `application_workflow` uses to fill in a
Source video's byte size, sampled-content fingerprint and duration; these
tests exercise it directly against real files on disk, independent of the
Analysis and the workflow that consume it.
"""

from __future__ import annotations

from pathlib import Path

from media_probe import FileMediaProbe, SAMPLE_SIZE


def test_probing_a_file_reports_its_byte_size(tmp_path: Path) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"x" * 10_000)

    probed = FileMediaProbe().probe(video_path)

    assert probed.byte_size == 10_000


def test_identical_content_produces_the_same_fingerprint(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    content = b"same content twice" * 1000
    first.write_bytes(content)
    second.write_bytes(content)

    probe = FileMediaProbe()

    assert probe.probe(first).fingerprint == probe.probe(second).fingerprint


def test_different_content_produces_different_fingerprints(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"a" * 10_000)
    second.write_bytes(b"b" * 10_000)

    probe = FileMediaProbe()

    assert probe.probe(first).fingerprint != probe.probe(second).fingerprint


def test_files_of_different_size_never_share_a_fingerprint(tmp_path: Path) -> None:
    """Size is folded into the digest, not just compared alongside it.

    Two files that happen to share every sampled byte region but differ in
    length must not collide — the digest has to depend on size too, or a
    truncated copy of a video could be mistaken for the original.
    """

    short = tmp_path / "short.mp4"
    long = tmp_path / "long.mp4"
    short.write_bytes(b"a" * SAMPLE_SIZE)
    long.write_bytes(b"a" * SAMPLE_SIZE * 3)

    probe = FileMediaProbe()

    assert probe.probe(short).fingerprint != probe.probe(long).fingerprint


def test_probing_never_reads_the_whole_file(tmp_path: Path) -> None:
    """A multi-gigabyte recording must not be read in full to be probed."""

    huge_video = tmp_path / "huge.mp4"
    with huge_video.open("wb") as handle:
        handle.seek(200 * SAMPLE_SIZE - 1)
        handle.write(b"\0")

    probed = FileMediaProbe().probe(huge_video)

    assert probed.byte_size == 200 * SAMPLE_SIZE
    assert probed.fingerprint


def test_a_file_moviepy_cannot_open_still_probes_size_and_fingerprint(
    tmp_path: Path,
) -> None:
    not_a_video = tmp_path / "notes.mp4"
    not_a_video.write_bytes(b"this is not a real media container")

    probed = FileMediaProbe().probe(not_a_video)

    assert probed.byte_size > 0
    assert probed.fingerprint
    assert probed.duration_ms is None
