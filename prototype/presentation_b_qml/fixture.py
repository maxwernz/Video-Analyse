"""The canonical prototype fixture, built as a real Analysis.

Both prototypes render the same Analysis so their screenshots can be compared.
Nothing here is a mock: the fixture goes through ``analysis.Analysis`` and
``AnalysisDocument`` exactly as the application does, which is half the point —
if the QML presentation layer needed a friendlier shape than the real domain
objects, that would show up here first.
"""

from __future__ import annotations

from pathlib import Path

from analysis import Analysis, AnalysisDocument, Clip

PROTOTYPE_ROOT = Path(__file__).resolve().parent
MEDIA = PROTOTYPE_ROOT / "media"

ANALYSIS_TITLE = "SG Beispiel - TV Muster"
PLAYHEAD_MS = 14 * 60_000 + 3_000
SELECTED_CLIP_NAME = "Tor von rechts außen"

#: Palette entries 1, 5, 7, 8 and 2 of the frozen Category palette.
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Angriff", "#E2564A"),
    ("Tor", "#4BA46A"),
    ("Siebenmeter", "#3E9BC4"),
    ("Abwehr", "#5B87D6"),
    ("Konter", "#DE8241"),
)

FIRST_HALF_DURATION_MS = 45 * 60_000
SECOND_HALF_DURATION_MS = 42 * 60_000 + 30_000


def _at(minutes: int, seconds: float = 0.0) -> int:
    return round((minutes * 60 + seconds) * 1000)


#: (Source video index, Category, name, start, end, notes)
CLIPS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (0, "Konter", "Schneller Gegenstoß", _at(3), _at(3, 12.4),
     "Zweite Welle läuft mit, Rückraum rechts zieht durch."),
    (0, "Siebenmeter", "Siebenmeter", _at(5), _at(5, 6.8), ""),
    (0, "Abwehr", "Abwehrfehler Mitte", _at(8), _at(8, 9.2),
     "Mitte rückt nicht heraus, Lücke zwischen Halb und Mitte."),
    (0, "Tor", SELECTED_CLIP_NAME, _at(14), _at(14, 7.5),
     "Rückraum rechts, Tempogegenstoß nach Ballgewinn."),
    # Starts 4.5s after the Clip above ends: at 45 minutes across a 1200px
    # timeline the two ranges are about two pixels apart, which is the
    # minimum-width limitation ADR 0006 records, made visible on purpose.
    (0, "Angriff", "Nachwurf nach Block", _at(14, 12), _at(14, 34),
     "Langer Angriff, zweiter Nachwurf über den Kreis."),
    (0, "Abwehr", "Doppelter Block", _at(21), _at(21, 11), ""),
    (0, "Angriff", "Kreisläufer freigespielt", _at(27, 30), _at(27, 44),
     "Kreuzbewegung bindet den Halben, Kreis steht frei."),
    (0, "Konter", "Konter über links", _at(30), _at(30, 10), ""),
    (0, "Tor", "Tor nach Kreuzen", _at(38, 20), _at(38, 37), ""),
    (1, "Konter", "Gegenstoß nach Fehlpass", _at(4, 15), _at(4, 23.5), ""),
    (1, "Abwehr", "Abwehr 3-2-1 gestaffelt", _at(16, 40), _at(16, 59),
     "Offensive Deckung greift den Rückraum früh an."),
    (1, "Tor", "Tor vom Kreis", _at(33, 5), _at(33, 21), ""),
)


def canonical_document() -> AnalysisDocument:
    """The populated Analysis both prototypes render."""
    analysis = Analysis(ANALYSIS_TITLE)
    first = analysis.add_source_video(
        "halbzeit-1.mp4",
        str(MEDIA / "halbzeit-1.mp4"),
        duration_ms=FIRST_HALF_DURATION_MS,
    )
    second = analysis.add_source_video(
        "halbzeit-2.mp4",
        str(MEDIA / "halbzeit-2.mp4"),
        duration_ms=SECOND_HALF_DURATION_MS,
    )
    for name, color in CATEGORIES:
        analysis.add_category(name, color)
    sources = (first, second)
    for video_index, category_name, name, start_ms, end_ms, notes in CLIPS:
        category = analysis.category_named(category_name)
        assert category is not None
        analysis.add_clip(
            sources[video_index].id,
            name,
            start_ms,
            end_ms,
            notes=notes,
            category_id=category.id,
        )
    return AnalysisDocument(analysis)


def empty_document() -> AnalysisDocument:
    """An Analysis with no Source videos, for the designed empty state."""
    analysis = Analysis("")
    for name, color in CATEGORIES[:3]:
        analysis.add_category(name, color)
    return AnalysisDocument(analysis)


def selected_clip(analysis: Analysis) -> Clip:
    return next(clip for clip in analysis.clips if clip.name == SELECTED_CLIP_NAME)


def media_is_present() -> bool:
    return (MEDIA / "halbzeit-1.mp4").is_file()
