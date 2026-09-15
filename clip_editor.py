"""The Clip being edited, held apart from the Analysis until it is kept.

Editing works on a copy. That is what makes a cancelled edit cost nothing —
there is no undo to write, because the Analysis was never told — and it is
what lets a scrub-linked boundary move the video to a dozen frames on the way
to the right one without a dozen revisions reaching the document.

The rules about a draft live here rather than in the view model, so that "an
end before its start is refused" and "a Clip needs a title" are statements
about a Clip rather than about a form. The view model owns what those mean for
the video and the Analysis; this module owns what they are.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from analysis import Analysis, Clip
from item_models import RoleModel


#: The shortest Clip two presses of the mark action can produce.
#:
#: Two presses on the same frame are an analyst marking a moment rather than
#: an interval, and an Analysis will not accept a Clip that ends where it
#: begins. A fifth of a second is short enough to read as "here" and long
#: enough to be a Clip.
MINIMUM_CLIP_MS = 200

#: What a newly marked Clip is called before the analyst names it.
#:
#: A name rather than an empty field, because the form opens with the title
#: already valid: the analyst who only wanted the boundaries can press Save.
NEW_CLIP_NAME = "Neuer Clip"

#: The two boundaries, as QML names them.
START = "start"
END = "end"

#: Why a Clip cannot be kept, or a boundary cannot be moved, in the words the
#: form shows. They are here with the rules that produce them.
NO_TITLE = "Ein Clip braucht einen Titel."
END_BEFORE_START = "Das Ende muss nach dem Start liegen."
NOT_A_TIME = "Das ist keine Zeit, die ein Clip haben kann."


@dataclass(frozen=True, slots=True)
class ClipDraft:
    """One Clip's worth of edits, before the Analysis has heard about them."""

    source_video_id: UUID
    name: str
    start_ms: int
    end_ms: int
    notes: str
    category_id: UUID | None
    clip_id: UUID | None = None

    @classmethod
    def of(cls, clip: Clip) -> ClipDraft:
        """The draft that edits an existing Clip."""

        return cls(
            source_video_id=clip.source_video_id,
            name=clip.name,
            start_ms=clip.start_ms,
            end_ms=clip.end_ms,
            notes=clip.notes,
            category_id=clip.category_id,
            clip_id=clip.id,
        )

    @classmethod
    def marked(
        cls, source_video_id: UUID, first_ms: int, second_ms: int, *, limit_ms: int
    ) -> ClipDraft:
        """The draft two marked boundaries make, in either order.

        An analyst who saw the moment and rewound has marked the same Clip as
        one who marked it going forwards, so the two presses are an interval
        rather than a start and an end. Two presses on one frame still make a
        Clip, and one marked at the final whistle stays inside the recording.
        """

        start = max(0, min(first_ms, second_ms))
        end = max(first_ms, second_ms)
        if end - start < MINIMUM_CLIP_MS:
            end = start + MINIMUM_CLIP_MS
        if limit_ms > 0:
            end = min(end, limit_ms)
            start = min(start, max(0, end - MINIMUM_CLIP_MS))
        return cls(
            source_video_id=source_video_id,
            name=NEW_CLIP_NAME,
            start_ms=start,
            end_ms=end,
            notes="",
            category_id=None,
        )

    @property
    def is_new(self) -> bool:
        """Whether keeping this draft adds a Clip or changes one."""

        return self.clip_id is None

    @property
    def length_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    @property
    def error(self) -> str:
        """Why this draft cannot be kept, or nothing if it can."""

        return "" if self.name.strip() else NO_TITLE

    def boundary_ms(self, which: str) -> int:
        return self.start_ms if which == START else self.end_ms

    def with_boundary(
        self, which: str, value_ms: int | None, *, limit_ms: int
    ) -> ClipDraft | None:
        """One boundary moved, or nothing when the move would invert the Clip.

        Refusing is deliberate. Silently swapping the boundaries, or clamping
        one against the other, moves a cut the analyst did not ask to move and
        leaves them reading a number they did not type; the form says what
        went wrong instead and keeps the Clip it had.
        """

        if value_ms is None:
            return None
        value = max(0, int(value_ms))
        if limit_ms > 0:
            value = min(value, limit_ms)
        if which == START:
            return None if value >= self.end_ms else replace(self, start_ms=value)
        return None if value <= self.start_ms else replace(self, end_ms=value)


class CategoryModel(RoleModel):
    """The Analysis-wide Categories, for the Clip editor's chooser.

    A fixed set of chips rather than a colour picker: ADR 0007 took the free
    colour choice away, so what an analyst picks here is one of the Categories
    the Analysis already has.
    """

    ROLES = ("categoryId", "name", "color", "selected")

    def refresh(self, analysis: Analysis, *, selected_category_id: UUID | None) -> None:
        self._replace(
            [
                {
                    "categoryId": str(category.id),
                    "name": category.name,
                    "color": category.color,
                    "selected": category.id == selected_category_id,
                }
                for category in analysis.categories
            ]
        )


__all__ = [
    "END",
    "END_BEFORE_START",
    "MINIMUM_CLIP_MS",
    "NEW_CLIP_NAME",
    "NOT_A_TIME",
    "NO_TITLE",
    "START",
    "CategoryModel",
    "ClipDraft",
]
