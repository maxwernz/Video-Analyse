"""THROWAWAY PROTOTYPE A -- the canonical fixture from the frozen tokens.

Built on the real ``analysis.Analysis`` rather than prototype-local dataclasses,
because one of the decision criteria is how well a presentation layer sits on
the existing domain seams. If this fixture cannot be expressed through the real
model, that is a finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from analysis.model import Analysis, Clip

from . import tokens

TITLE = "SG Beispiel - TV Muster"

HALBZEIT_1_DURATION_MS = 45 * 60 * 1000
HALBZEIT_2_DURATION_MS = (42 * 60 + 30) * 1000

PLAYHEAD_MS = (14 * 60 + 3) * 1000
SELECTED_CLIP_NAME = "Tor von rechts außen"

# Categories drawn from palette entries 1, 5, 7, 8, 2, as the tokens require.
_CATEGORIES: tuple[tuple[str, int], ...] = (
    ("Tor", 1),
    ("Angriff", 5),
    ("Abwehr", 7),
    ("Konter", 8),
    ("Siebenmeter", 2),
)


def _ms(minutes: int, seconds: int) -> int:
    return (minutes * 60 + seconds) * 1000


# (source index, category, name, start, end, notes)
_CLIPS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (0, "Angriff", "Schneller Gegenstoß", _ms(3, 0), _ms(3, 12), ""),
    (0, "Siebenmeter", "Siebenmeter gehalten", _ms(5, 0), _ms(5, 6), ""),
    (0, "Abwehr", "Abwehrfehler Mitte", _ms(8, 0), _ms(8, 9), ""),
    (
        0,
        "Tor",
        SELECTED_CLIP_NAME,
        _ms(14, 0),
        _ms(14, 7),
        "Rückraum rechts, Tempogegenstoß nach Ballgewinn.",
    ),
    # Five seconds after the Clip above ends: the pair the tokens ask for, so
    # the minimum-range-width behaviour is visible on the timeline.
    (0, "Tor", "Nachwurf zum Ausgleich", _ms(14, 12), _ms(14, 20), ""),
    (0, "Abwehr", "Doppelter Block", _ms(21, 0), _ms(21, 11), ""),
    (0, "Angriff", "Kreisläufer angespielt", _ms(27, 30), _ms(27, 52), ""),
    (0, "Konter", "Konter über links", _ms(30, 0), _ms(30, 10), ""),
    (1, "Konter", "Tempogegenstoß nach Fehlpass", _ms(4, 20), _ms(4, 34), ""),
    (1, "Tor", "Tor nach Kreuzbewegung", _ms(12, 5), _ms(12, 23), ""),
    (1, "Abwehr", "Zeitstrafe Nummer 7", _ms(19, 40), _ms(19, 47), ""),
    (1, "Siebenmeter", "Siebenmeter verworfen", _ms(33, 10), _ms(33, 26), ""),
)


@dataclass
class Fixture:
    analysis: Analysis
    active_source_video_id: UUID
    selected_clip_id: UUID
    playhead_ms: int

    def selected_clip(self) -> Clip:
        return self.analysis.clip(self.selected_clip_id)


def build(
    *,
    media_locations: dict[str, str] | None = None,
    media_durations: dict[str, int] | None = None,
) -> Fixture:
    """The one Analysis both prototypes render.

    ``media_locations`` swaps in real files when the prototype is run against
    real media; without it the locations are names only and playback is faked.
    ``media_durations`` additionally scales the Clip times into the real files,
    so a short measurement clip still shows a sensible timeline instead of
    twelve Clips beyond its end.
    """
    media_locations = media_locations or {}
    media_durations = media_durations or {}
    analysis = Analysis(TITLE)

    canonical = {
        "halbzeit-1.mp4": HALBZEIT_1_DURATION_MS,
        "halbzeit-2.mp4": HALBZEIT_2_DURATION_MS,
    }
    scales: dict[int, float] = {}

    sources = []
    for index, (name, duration) in enumerate(canonical.items()):
        actual = media_durations.get(name, duration)
        scales[index] = actual / duration
        sources.append(
            analysis.add_source_video(
                name.removesuffix(".mp4"),
                media_locations.get(name, f"/Volumes/Spiele/{name}"),
                duration_ms=actual,
            )
        )

    categories = {
        name: analysis.add_category(name, tokens.CATEGORY_PALETTE[entry - 1][1])
        for name, entry in _CATEGORIES
    }

    selected: UUID | None = None
    for source_index, category, name, start, end, notes in _CLIPS:
        scale = scales[source_index]
        clip = analysis.add_clip(
            sources[source_index].id,
            name,
            int(start * scale),
            int(end * scale),
            notes=notes,
            category_id=categories[category].id,
        )
        if name == SELECTED_CLIP_NAME:
            selected = clip.id

    assert selected is not None
    return Fixture(
        analysis=analysis,
        active_source_video_id=sources[0].id,
        selected_clip_id=selected,
        playhead_ms=int(PLAYHEAD_MS * scales[0]),
    )


def timecode(position_ms: int) -> str:
    """HH:MM:SS, the form the shipped interface and the reference both use."""
    total_seconds, _ = divmod(max(0, int(position_ms)), 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def precise_timecode(position_ms: int) -> str:
    """HH:MM:SS.mmm, for the Clip editor's boundary fields."""
    milliseconds = max(0, int(position_ms)) % 1000
    return f"{timecode(position_ms)}.{milliseconds:03d}"


def duration_text(duration_ms: int) -> str:
    """A duration reads as seconds until it needs minutes; never as a clock."""
    seconds = duration_ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s".replace(".0s", "s")
    minutes, remaining = divmod(int(round(seconds)), 60)
    return f"{minutes}:{remaining:02d}"
