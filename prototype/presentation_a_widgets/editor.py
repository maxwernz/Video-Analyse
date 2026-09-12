"""THROWAWAY PROTOTYPE A -- the Clip-editing form.

360px, sectioned with rules, monospace boundary fields sized for a full
timecode with a live duration readout, and an action row that resolves to one
accent primary and a quiet secondary. The shipped editor clipped its boundary
fields so that only ``:00.000`` was visible; these are measured from the font.
"""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from analysis.model import Analysis, Category, Clip

from . import controls, fixture, fonts, icons, tokens

START = "start"
END = "end"


class CategoryButton(QToolButton):
    """Category as a menu button carrying its own colour chip."""

    category_chosen = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._category: Category | None = None
        self.setPopupMode(QToolButton.InstantPopup)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(tokens.CONTROL_HEIGHT)
        # Painted entirely by hand, so it has no text or icon to size itself
        # from and must be told to fill the form's column.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._font = fonts.ui(tokens.SIZE_BODY, tokens.WEIGHT_REGULAR)

    def show_categories(self, categories: tuple[Category, ...], current: Category | None) -> None:
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for category in categories:
            action = QAction(category.name, menu)
            action.setCheckable(True)
            action.setChecked(current is not None and category.id == current.id)
            action.setIcon(icons.icon("tag", category.color, tokens.ICON_SIZE_DEFAULT))
            action.triggered.connect(
                lambda _checked, chosen=category: self._choose(chosen)
            )
            group.addAction(action)
            menu.addAction(action)
        self.setMenu(menu)
        self._category = current
        self.update()

    def _choose(self, category: Category) -> None:
        self._category = category
        self.update()
        self.category_chosen.emit(category)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)

        ground = tokens.CONTROL_HOVER if self.underMouse() else tokens.CONTROL
        painter.setPen(QColor(tokens.CONTROL_BORDER))
        painter.setBrush(QColor(ground))
        painter.drawRoundedRect(rect, tokens.RADIUS, tokens.RADIUS)

        left = rect.left() + 9
        if self._category is not None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self._category.color))
            painter.drawRect(QRect(left, rect.center().y() - 5, 3, 11))
            left += 3 + 9

        painter.setFont(self._font)
        painter.setPen(QColor(tokens.TEXT if self._category else tokens.TEXT_FAINT))
        painter.drawText(
            QRect(left, rect.top(), rect.right() - left - 20, rect.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._category.name if self._category else "Ohne Kategorie",
        )
        size = 12
        painter.drawPixmap(
            QRect(rect.right() - 17, rect.center().y() - size // 2, size, size),
            icons.tinted("chevron-down", tokens.TEXT_MUTED, size),
        )
        painter.end()


class ClipEditor(QWidget):
    """The right-hand form of the dedicated Clip-editing state."""

    boundary_scrubbed = Signal(int)
    saved = Signal()
    discarded = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Editor")
        self.setFixedWidth(tokens.EDITOR_WIDTH)

        self._analysis: Analysis | None = None
        self._clip: Clip | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(tokens.GUTTER, tokens.GUTTER, tokens.GUTTER, tokens.GUTTER)
        layout.setSpacing(0)

        heading = QLabel("Clip bearbeiten", self)
        heading.setProperty("role", "documentTitle")
        layout.addWidget(heading)
        layout.addSpacing(tokens.GUTTER)
        layout.addWidget(_rule(self))
        layout.addSpacing(tokens.GUTTER)

        layout.addWidget(controls.section_label("Titel", self))
        layout.addSpacing(6)
        self._title = QLineEdit(self)
        self._title.setPlaceholderText("Clip benennen")
        layout.addWidget(self._title)

        layout.addSpacing(tokens.GUTTER)
        layout.addWidget(controls.section_label("Kategorie", self))
        layout.addSpacing(6)
        self._category = CategoryButton(self)
        layout.addWidget(self._category)

        layout.addSpacing(tokens.GUTTER)
        layout.addWidget(_rule(self))
        layout.addSpacing(tokens.GUTTER)

        boundaries_header = QHBoxLayout()
        boundaries_header.setContentsMargins(0, 0, 0, 0)
        boundaries_header.addWidget(controls.section_label("Grenzen", self))
        boundaries_header.addStretch(1)
        self._duration = controls.timecode_label("0s", muted=True)
        self._duration.setToolTip("Dauer")
        boundaries_header.addWidget(self._duration)
        layout.addLayout(boundaries_header)
        layout.addSpacing(6)

        boundaries = QHBoxLayout()
        boundaries.setContentsMargins(0, 0, 0, 0)
        boundaries.setSpacing(tokens.CONTROL_GAP)
        self._start = _boundary_field(self)
        self._end = _boundary_field(self)
        separator = QLabel("bis", self)
        separator.setProperty("role", "muted")
        boundaries.addWidget(self._start, 1)
        boundaries.addWidget(separator)
        boundaries.addWidget(self._end, 1)
        layout.addLayout(boundaries)

        layout.addSpacing(6)
        hint = QLabel("Beim Ändern springt das Video an diese Stelle.", self)
        hint.setProperty("role", "faint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addSpacing(tokens.GUTTER)
        layout.addWidget(_rule(self))
        layout.addSpacing(tokens.GUTTER)

        layout.addWidget(controls.section_label("Notizen", self))
        layout.addSpacing(6)
        self._notes = QTextEdit(self)
        self._notes.setPlaceholderText("Beobachtung festhalten")
        self._notes.setFixedHeight(120)
        layout.addWidget(self._notes)
        layout.addStretch(1)

        layout.addSpacing(tokens.GUTTER)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(tokens.CONTROL_GAP)
        discard = QPushButton("Verwerfen", self)
        discard.setProperty("kind", "quiet")
        discard.setCursor(Qt.PointingHandCursor)
        discard.clicked.connect(self.discarded.emit)
        save = QPushButton("Clip sichern", self)
        save.setProperty("kind", "primary")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self.saved.emit)
        actions.addStretch(1)
        actions.addWidget(discard)
        actions.addWidget(save)
        layout.addLayout(actions)

        self._start.textEdited.connect(lambda _text: self._boundary_edited(START))
        self._end.textEdited.connect(lambda _text: self._boundary_edited(END))

    def show_clip(self, analysis: Analysis, clip: Clip) -> None:
        self._analysis = analysis
        self._clip = clip
        self._title.setText(clip.name)
        self._start.setText(fixture.precise_timecode(clip.start_ms))
        self._end.setText(fixture.precise_timecode(clip.end_ms))
        self._notes.setPlainText(clip.notes)
        category = (
            analysis.category(clip.category_id) if clip.category_id is not None else None
        )
        self._category.show_categories(analysis.categories, category)
        self._refresh_duration()

    def _boundary_edited(self, which: str) -> None:
        field = self._start if which == START else self._end
        parsed = _parse_timecode(field.text())
        if parsed is None:
            return
        self._refresh_duration()
        # Scrub-linked: adjusting a boundary moves the video to that frame.
        self.boundary_scrubbed.emit(parsed)

    def _refresh_duration(self) -> None:
        start = _parse_timecode(self._start.text())
        end = _parse_timecode(self._end.text())
        if start is None or end is None:
            self._duration.setText("--")
            return
        self._duration.setText(fixture.duration_text(max(0, end - start)))


def _boundary_field(parent: QWidget) -> QLineEdit:
    """A boundary field measured from its own font, so it cannot clip."""
    field = QLineEdit(parent)
    field.setProperty("role", "timecode")
    field.setFont(fonts.mono(tokens.SIZE_TIMECODE, tokens.WEIGHT_MEDIUM))
    field.setAlignment(Qt.AlignCenter)
    metrics = QFontMetrics(field.font())
    field.setMinimumWidth(metrics.horizontalAdvance("00:00:00.000") + 22)
    return field


def _parse_timecode(text: str) -> int | None:
    parts = text.strip().split(":")
    if len(parts) != 3:
        return None
    seconds_part = parts[2]
    milliseconds = 0
    if "." in seconds_part:
        seconds_part, fraction = seconds_part.split(".", 1)
        if not fraction.isdigit():
            return None
        milliseconds = int(f"{fraction:0<3.3}")
    if not (parts[0].isdigit() and parts[1].isdigit() and seconds_part.isdigit()):
        return None
    return (
        int(parts[0]) * 3_600_000
        + int(parts[1]) * 60_000
        + int(seconds_part) * 1000
        + milliseconds
    )


def _rule(parent: QWidget) -> QFrame:
    rule = QFrame(parent)
    rule.setProperty("role", "rule")
    rule.setFixedHeight(tokens.BORDER)
    return rule
