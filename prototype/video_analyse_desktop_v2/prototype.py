"""THROWAWAY PROTOTYPE — restrained desktop workspace, iteration two.

Three variants test Clips/Videos navigation, clickable Clip timelines, and richer
post-marking Clip editors. The visual language is flat, quiet, and intentionally
separate from production code.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


CAPTURE_DIR = Path(__file__).parent / "screenshots"

BG = "#191B1E"
SURFACE = "#212428"
SURFACE_ALT = "#272A2F"
SURFACE_ACTIVE = "#30343A"
LINE = "#3B3F45"
TEXT = "#F0F0EE"
MUTED = "#A1A4A8"
ACCENT = "#5D8FC7"
ACCENT_SOFT = "#344B65"
ERROR = "#D77A80"


@dataclass(frozen=True)
class Source:
    short: str
    name: str
    date: str
    duration: str


@dataclass(frozen=True)
class Clip:
    title: str
    category: str
    source: int
    start_s: int
    start: str
    duration: str
    note: str


SOURCES = [
    Source("V1", "TV A — Opponent B", "03.09.2026", "01:18:42"),
    Source("V2", "Opponent B — TSV C", "28.08.2026", "01:27:06"),
    Source("V3", "SV D — Opponent B", "20.08.2026", "00:58:19"),
]

CLIPS = [
    Clip("Kreuzung Rückraum", "Angriff", 0, 258, "00:04:18.12", "00:11.08", "RL bindet zwei Spieler."),
    Clip("2. Welle über links", "Gegenstoß", 1, 582, "00:09:42.03", "00:08.17", "Schneller Anwurf."),
    Clip("6:0 verschiebt spät", "Abwehr", 0, 786, "00:13:06.21", "00:14.02", "Halbrechts kommt zu spät."),
    Clip("Parade kurze Ecke", "Torwart", 2, 1012, "00:16:52.08", "00:06.10", "Torwart bleibt lange stehen."),
    Clip("Einlaufen Außen", "Angriff", 1, 1274, "00:21:14.19", "00:12.06", "Variante nach Timeout."),
    Clip("Ballverlust Mitte", "Fehler", 0, 1651, "00:27:31.04", "00:07.13", "Passweg früh erkennbar."),
    Clip("Rückzug ungeordnet", "Rückzug", 2, 1869, "00:31:09.16", "00:10.04", "Zentrum bleibt offen."),
    Clip("Überzahl 4 gegen 3", "Überzahl", 1, 2182, "00:36:22.02", "00:16.14", "Breite fehlt."),
    Clip("Unterzahl kompakt", "Unterzahl", 0, 2568, "00:42:48.11", "00:18.09", "Gute Blockarbeit."),
    Clip("Siebenmeter links", "Siebenmeter", 1, 2943, "00:49:03.07", "00:05.18", "Blick früh zur Ecke."),
    Clip("Kreis nach Sperre", "Angriff", 0, 3219, "00:53:39.22", "00:09.03", "Sperre-Absetzen."),
    Clip("Offensive Deckung", "Abwehr", 1, 3680, "01:01:20.15", "00:13.11", "Vorziehen gegen RM."),
]

CATEGORY_COLORS = {
    "Angriff": "#B9786E",
    "Abwehr": "#6F9B91",
    "Gegenstoß": "#B69658",
    "Torwart": "#79966C",
    "Fehler": "#A86C79",
    "Rückzug": "#817B9E",
    "Überzahl": "#668AA2",
    "Unterzahl": "#8B7192",
    "Siebenmeter": "#A37E5E",
}


def text(value: str, role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(value)
    if role:
        widget.setProperty("role", role)
    widget.setWordWrap(wrap)
    return widget


def button(value: str, role: str = "button") -> QPushButton:
    widget = QPushButton(value)
    widget.setProperty("role", role)
    widget.setCursor(Qt.PointingHandCursor)
    return widget


def panel(role: str = "panel") -> QFrame:
    widget = QFrame()
    widget.setProperty("role", role)
    return widget


def rule(vertical: bool = False) -> QFrame:
    widget = QFrame()
    widget.setFrameShape(QFrame.VLine if vertical else QFrame.HLine)
    widget.setProperty("role", "rule")
    return widget


class VideoView(QWidget):
    def __init__(self, source: Source, frozen: bool = False):
        super().__init__()
        self.source = source
        self.frozen = frozen
        self.setMinimumSize(420, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = QRectF(self.rect())
        painter.fillRect(bounds, QColor("#101113"))
        court = bounds.adjusted(bounds.width() * .09, bounds.height() * .12, -bounds.width() * .09, -bounds.height() * .10)
        painter.fillRect(court, QColor("#78624E"))
        painter.setPen(QPen(QColor("#BBAA94"), 1.5))
        painter.drawRect(court)
        painter.drawLine(QPointF(court.center().x(), court.top()), QPointF(court.center().x(), court.bottom()))
        painter.drawEllipse(court.center(), court.height() * .12, court.height() * .12)
        for x, y, color in [(.31, .43, "#7CA1BA"), (.39, .61, "#7CA1BA"), (.62, .42, "#B27478"), (.69, .57, "#B27478")]:
            painter.setBrush(QColor(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(court.left() + court.width() * x, court.top() + court.height() * y), 6, 6)
        painter.fillRect(QRectF(0, 0, bounds.width(), 30), QColor("#181A1D"))
        painter.setPen(QColor(MUTED))
        painter.setFont(QFont("", 9))
        painter.drawText(QRectF(10, 0, bounds.width() - 20, 30), Qt.AlignVCenter | Qt.AlignLeft, self.source.name)
        painter.setPen(QColor(TEXT))
        painter.drawText(QRectF(10, 0, bounds.width() - 20, 30), Qt.AlignVCenter | Qt.AlignRight, "TVA 18  —  16 OPP")
        if self.frozen:
            painter.fillRect(bounds, QColor(15, 16, 18, 55))
            painter.setPen(QColor(TEXT))
            painter.drawText(QRectF(12, 38, 140, 24), Qt.AlignLeft, "PAUSED FRAME")


class GoalMap(QWidget):
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.origin = QPointF(.30, .64)
        self.target = QPointF(.79, .38)
        self.setMinimumHeight(150)
        self.setMouseTracking(True)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.fillRect(bounds, QColor("#1D2024"))
        painter.setPen(QPen(QColor(LINE), 1))
        painter.drawRect(bounds)
        split = bounds.left() + bounds.width() * .55
        painter.drawLine(QPointF(split, bounds.top()), QPointF(split, bounds.bottom()))

        court = QRectF(bounds.left() + 18, bounds.top() + 30, bounds.width() * .55 - 36, bounds.height() - 48)
        painter.setPen(QPen(QColor("#666A70"), 1))
        painter.drawArc(court.adjusted(court.width() * .48, 2, 0, -2), 90 * 16, 180 * 16)
        painter.drawLine(QPointF(court.left(), court.bottom()), QPointF(court.right(), court.bottom()))
        painter.setPen(QColor(MUTED))
        painter.setFont(QFont("", 8))
        painter.drawText(QRectF(bounds.left() + 10, bounds.top() + 7, bounds.width() * .5, 18), "WURFPOSITION")

        goal = QRectF(split + 30, bounds.top() + 38, bounds.right() - split - 58, bounds.height() - 66)
        painter.setPen(QPen(QColor("#84878B"), 2))
        painter.drawRect(goal)
        painter.setPen(QPen(QColor("#3D4146"), 1))
        for fraction in (.25, .5, .75):
            painter.drawLine(QPointF(goal.left() + goal.width() * fraction, goal.top()), QPointF(goal.left() + goal.width() * fraction, goal.bottom()))
            painter.drawLine(QPointF(goal.left(), goal.top() + goal.height() * fraction), QPointF(goal.right(), goal.top() + goal.height() * fraction))
        painter.setPen(QColor(MUTED))
        painter.drawText(QRectF(split + 10, bounds.top() + 7, bounds.right() - split - 20, 18), "TREFFERPUNKT")

        origin = QPointF(bounds.left() + bounds.width() * self.origin.x(), bounds.top() + bounds.height() * self.origin.y())
        target = QPointF(bounds.left() + bounds.width() * self.target.x(), bounds.top() + bounds.height() * self.target.y())
        painter.setBrush(QColor(ACCENT))
        painter.setPen(QPen(QColor(TEXT), 1))
        painter.drawEllipse(origin, 6, 6)
        painter.setBrush(QColor("#B9786E"))
        painter.drawEllipse(target, 6, 6)
        painter.setPen(QPen(QColor("#72767B"), 1, Qt.DashLine))
        painter.drawLine(origin, target)

    def mousePressEvent(self, event):  # noqa: N802
        x = event.position().x() / max(1, self.width())
        y = event.position().y() / max(1, self.height())
        if x < .55:
            self.origin = QPointF(max(.06, x), max(.18, min(.90, y)))
            label = "Wurfposition gesetzt"
        else:
            self.target = QPointF(max(.60, min(.94, x)), max(.18, min(.88, y)))
            label = "Trefferpunkt gesetzt"
        self.changed.emit(label)
        self.update()


class ClipTimeline(QWidget):
    clip_clicked = Signal(int)

    def __init__(self, mode: str, selected: int):
        super().__init__()
        self.mode = mode
        self.selected = selected
        self.hit_rects: list[tuple[QRectF, int]] = []
        self.setMinimumHeight(92 if mode == "lanes" else 78)
        self.setMaximumHeight(124 if mode == "lanes" else 96)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(SURFACE))
        self.hit_rects = []
        width = max(100, self.width() - 78)
        left = 60
        if self.mode == "lanes":
            for source_index, source in enumerate(SOURCES):
                y = 18 + source_index * 27
                painter.setPen(QColor(MUTED))
                painter.setFont(QFont("", 8, QFont.DemiBold))
                painter.drawText(QRectF(9, y - 8, 40, 18), Qt.AlignRight | Qt.AlignVCenter, source.short)
                painter.setPen(QPen(QColor("#35393E"), 1))
                painter.drawLine(QPointF(left, y + 8), QPointF(left + width, y + 8))
                for index, clip in enumerate(CLIPS):
                    if clip.source != source_index:
                        continue
                    x = left + width * (clip.start_s / 4700)
                    block = QRectF(x, y, max(18, width * .025), 16)
                    self._draw_block(painter, block, index)
        else:
            y = 34
            painter.setPen(QPen(QColor("#3C4045"), 2))
            painter.drawLine(QPointF(left, y + 11), QPointF(left + width, y + 11))
            painter.setPen(QColor(MUTED))
            painter.setFont(QFont("", 8))
            painter.drawText(QRectF(8, y - 1, 42, 20), Qt.AlignRight | Qt.AlignVCenter, "CLIPS")
            for index, clip in enumerate(CLIPS):
                x = left + width * (clip.start_s / 4700)
                block = QRectF(x, y, max(18, width * .026), 22)
                self._draw_block(painter, block, index)
            selected_clip = CLIPS[self.selected]
            painter.setPen(QColor(TEXT))
            painter.setFont(QFont("", 9, QFont.DemiBold))
            painter.drawText(QRectF(left, 5, width, 22), Qt.AlignLeft, f"{selected_clip.title}   {selected_clip.start}   ·   {SOURCES[selected_clip.source].short}")
        painter.setPen(QColor("#777A7E"))
        painter.setFont(QFont("", 8))
        painter.drawText(QRectF(left, self.height() - 19, width, 16), Qt.AlignLeft, "00:00")
        painter.drawText(QRectF(left, self.height() - 19, width, 16), Qt.AlignRight, "01:18:42")

    def _draw_block(self, painter: QPainter, rect: QRectF, index: int):
        color = QColor(CATEGORY_COLORS[CLIPS[index].category])
        painter.setBrush(color)
        painter.setPen(QPen(QColor(TEXT) if index == self.selected else color, 2 if index == self.selected else 1))
        painter.drawRect(rect)
        if index == self.selected:
            painter.fillRect(QRectF(rect.left(), rect.bottom() + 3, rect.width(), 2), QColor(ACCENT))
        self.hit_rects.append((rect.adjusted(-4, -5, 4, 5), index))

    def mousePressEvent(self, event):  # noqa: N802
        point = event.position()
        matches = [(rect.center().x() - point.x()) ** 2 + (rect.center().y() - point.y()) ** 2 for rect, _ in self.hit_rects]
        if matches:
            _, index = self.hit_rects[min(range(len(matches)), key=matches.__getitem__)]
            self.clip_clicked.emit(index)


class ClipRow(QFrame):
    chosen = Signal(int)

    def __init__(self, index: int, selected: bool):
        super().__init__()
        clip = CLIPS[index]
        self.index = index
        self.setProperty("role", "clipSelected" if selected else "clip")
        self.setMinimumHeight(43)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)
        marker = QFrame()
        marker.setFixedSize(3, 28)
        marker.setStyleSheet(f"background:{CATEGORY_COLORS[clip.category]}")
        layout.addWidget(marker)
        words = QVBoxLayout()
        words.setSpacing(1)
        words.addWidget(text(clip.title, "itemTitle"))
        words.addWidget(text(f"{clip.start}  ·  {clip.category}  ·  {SOURCES[clip.source].short}", "micro"))
        layout.addLayout(words, 1)
        layout.addWidget(text("›", "muted"))

    def mousePressEvent(self, event):  # noqa: N802
        self.chosen.emit(self.index)


class PrototypeWindow(QMainWindow):
    VARIANTS = {
        "A": "Tabbed library + modal",
        "B": "Video tabs + editing dock",
        "C": "Source lanes + edit workspace",
    }

    def __init__(self, variant: str = "A", editor: bool = False):
        super().__init__()
        self.variant = variant
        self.editor_open = editor
        self.browser_tab = "clips"
        self.selected_clip = 2
        self.active_source = CLIPS[self.selected_clip].source
        self.pending_start: str | None = None
        self.status = "Ready"
        self.resize(1440, 900)
        self.setMinimumSize(1120, 680)
        self.setWindowTitle("Video Analyse — restrained UX prototype")
        self.setStyleSheet(STYLE)
        self._build_menu()
        shell = QWidget()
        self.setCentralWidget(shell)
        self.root = QVBoxLayout(shell)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.root.addWidget(self.content, 1)
        self.root.addWidget(self.build_switcher())
        QShortcut(QKeySequence("Meta+R"), self, activated=self.mark_clip)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.mark_clip)
        self.render()

    def _build_menu(self):
        for name, items in [
            ("Ablage", ["Neue Analyse", "Öffnen …", "Sichern", "Videos hinzufügen …", "Exportieren …"]),
            ("Bearbeiten", ["Rückgängig", "Wiederholen", "Clip bearbeiten", "Clip löschen"]),
            ("Darstellung", ["Seitenleiste", "Vollbild", "Sprache"]),
            ("Hilfe", ["Tastaturkurzbefehle", "Über Video Analyse"]),
        ]:
            menu = self.menuBar().addMenu(name)
            for item in items:
                menu.addAction(QAction(item, self))

    def build_switcher(self) -> QWidget:
        bar = panel("prototype")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(7)
        layout.addWidget(text("PROTOTYPE V2", "prototypeBadge"))
        previous = button("←", "prototypeButton")
        previous.clicked.connect(lambda: self.cycle_variant(-1))
        layout.addWidget(previous)
        self.variant_label = text("", "prototypeText")
        self.variant_label.setMinimumWidth(250)
        layout.addWidget(self.variant_label)
        following = button("→", "prototypeButton")
        following.clicked.connect(lambda: self.cycle_variant(1))
        layout.addWidget(following)
        layout.addWidget(rule(True))
        clips_tab = button("Clip-Liste", "prototypeButton")
        clips_tab.clicked.connect(lambda: self.set_browser_tab("clips"))
        layout.addWidget(clips_tab)
        videos_tab = button("Video-Liste", "prototypeButton")
        videos_tab.clicked.connect(lambda: self.set_browser_tab("videos"))
        layout.addWidget(videos_tab)
        editor = button("Editor öffnen/schließen", "prototypeButton")
        editor.clicked.connect(self.toggle_editor)
        layout.addWidget(editor)
        layout.addStretch()
        for label, width, height in [("1440×900", 1440, 900), ("1280×720", 1280, 720)]:
            size = button(label, "prototypeButton")
            size.clicked.connect(lambda checked=False, w=width, h=height: self.resize(w, h))
            layout.addWidget(size)
        self.state_label = text("", "prototypeState")
        self.state_label.setMinimumWidth(310)
        layout.addWidget(self.state_label)
        return bar

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            old = item.widget()
            if old:
                old.setParent(None)
                old.deleteLater()

    def render(self):
        self.clear_content()
        self.variant_label.setText(f"{self.variant} · {self.VARIANTS[self.variant]}")
        self.state_label.setText(
            f"state  variant={self.variant}  tab={self.browser_tab}  source={self.active_source + 1}  "
            f"clip={self.selected_clip + 1}  editor={'open' if self.editor_open else 'closed'}"
        )
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.build_header())
        if self.variant == "A":
            layout.addWidget(self.build_variant_a(), 1)
        elif self.variant == "B":
            layout.addWidget(self.build_variant_b(), 1)
        else:
            layout.addWidget(self.build_variant_c(), 1)
        self.content_layout.addWidget(page)

    def build_header(self) -> QWidget:
        header = panel("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(10)
        layout.addWidget(text("VIDEO ANALYSE", "product"))
        layout.addWidget(rule(True))
        layout.addWidget(text("Opponent B · Vorbereitung", "document"))
        layout.addWidget(text("UNSAVED", "unsaved"))
        layout.addStretch()
        self.live_status_label = text(self.status, "status")
        layout.addWidget(self.live_status_label)
        layout.addWidget(button("Sichern", "quiet"))
        layout.addWidget(button("Exportieren", "primary"))
        return header

    def build_variant_a(self) -> QWidget:
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = self.build_tabbed_library()
        sidebar.setFixedWidth(350 if self.width() >= 1400 else 330)
        layout.addWidget(sidebar)
        if self.editor_open:
            layout.addWidget(self.build_modal_editor(), 1)
        else:
            layout.addWidget(self.build_video_workspace("single"), 1)
        return body

    def build_variant_b(self) -> QWidget:
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        clips = self.build_compact_clip_pane()
        clips.setFixedWidth(300)
        layout.addWidget(clips)
        workspace = panel("workspace")
        work = QVBoxLayout(workspace)
        work.setContentsMargins(12, 10, 12, 10)
        work.setSpacing(8)
        work.addWidget(self.build_video_tabs())
        work.addWidget(VideoView(SOURCES[self.active_source], self.editor_open), 1)
        work.addWidget(self.build_transport())
        timeline = ClipTimeline("detail", self.selected_clip)
        timeline.clip_clicked.connect(self.select_clip)
        work.addWidget(timeline)
        if self.editor_open:
            work.addWidget(self.build_dock_editor())
        else:
            work.addWidget(self.build_marking_row())
        layout.addWidget(workspace, 1)
        return body

    def build_variant_c(self) -> QWidget:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if self.editor_open:
            layout.addWidget(self.build_full_editor(), 1)
        else:
            top = QWidget()
            row = QHBoxLayout(top)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            browser = self.build_tabbed_library()
            browser.setFixedWidth(320)
            row.addWidget(browser)
            workspace = panel("workspace")
            work = QVBoxLayout(workspace)
            work.setContentsMargins(12, 10, 12, 10)
            work.addWidget(VideoView(SOURCES[self.active_source]), 1)
            work.addWidget(self.build_transport())
            work.addWidget(self.build_marking_row())
            row.addWidget(workspace, 1)
            layout.addWidget(top, 1)
        timeline = ClipTimeline("lanes", self.selected_clip)
        timeline.clip_clicked.connect(self.select_clip)
        layout.addWidget(timeline)
        return body

    def build_tabbed_library(self) -> QWidget:
        pane = panel("sidebar")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tabs = QWidget()
        tab_layout = QHBoxLayout(tabs)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        clips = button(f"CLIPS  {len(CLIPS)}", "tabActive" if self.browser_tab == "clips" else "tab")
        clips.clicked.connect(lambda: self.set_browser_tab("clips"))
        videos = button(f"VIDEOS  {len(SOURCES)}", "tabActive" if self.browser_tab == "videos" else "tab")
        videos.clicked.connect(lambda: self.set_browser_tab("videos"))
        tab_layout.addWidget(clips)
        tab_layout.addWidget(videos)
        layout.addWidget(tabs)
        if self.browser_tab == "clips":
            layout.addWidget(self.build_clip_browser(), 1)
        else:
            layout.addWidget(self.build_video_browser(), 1)
        return pane

    def build_clip_browser(self) -> QWidget:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(7)
        search = QLineEdit()
        search.setPlaceholderText("Clips durchsuchen")
        layout.addWidget(search)
        filters = QHBoxLayout()
        source = QComboBox()
        source.addItems(["Alle Videos", "V1 · TV A", "V2 · Opponent B", "V3 · SV D"])
        category = QComboBox()
        category.addItems(["Alle Kategorien", "Angriff", "Abwehr", "Gegenstoß"])
        filters.addWidget(source)
        filters.addWidget(category)
        layout.addLayout(filters)
        layout.addWidget(text("ZEITLICHE REIHENFOLGE", "section"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        list_body = QWidget()
        list_layout = QVBoxLayout(list_body)
        list_layout.setContentsMargins(0, 0, 2, 0)
        list_layout.setSpacing(2)
        for index in range(len(CLIPS)):
            row = ClipRow(index, index == self.selected_clip)
            row.chosen.connect(self.select_clip)
            list_layout.addWidget(row)
        list_layout.addStretch()
        scroll.setWidget(list_body)
        layout.addWidget(scroll, 1)
        return body

    def build_video_browser(self) -> QWidget:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(0)
        toolbar = QHBoxLayout()
        toolbar.addWidget(text("QUELLVIDEOS", "section"))
        toolbar.addStretch()
        toolbar.addWidget(button("+ Video", "quiet"))
        layout.addLayout(toolbar)
        layout.addSpacing(6)
        for index, source in enumerate(SOURCES):
            row = button("", "videoRowActive" if index == self.active_source else "videoRow")
            row.setMinimumHeight(78)
            content = QHBoxLayout(row)
            content.setContentsMargins(8, 8, 8, 8)
            thumb = QFrame()
            thumb.setFixedSize(84, 52)
            thumb.setStyleSheet("background:#41454A; border:1px solid #565A5F")
            content.addWidget(thumb)
            words = QVBoxLayout()
            words.addWidget(text(source.name, "itemTitle"))
            words.addWidget(text(f"{source.date}  ·  {source.duration}", "micro"))
            words.addWidget(text(f"{sum(1 for clip in CLIPS if clip.source == index)} Clips", "muted"))
            content.addLayout(words, 1)
            row.clicked.connect(lambda checked=False, i=index: self.select_source(i))
            layout.addWidget(row)
        layout.addStretch()
        footer = text("Ein Clip gehört immer genau zu einem Quellvideo.", "micro", True)
        layout.addWidget(footer)
        return body

    def build_compact_clip_pane(self) -> QWidget:
        pane = panel("sidebar")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(9, 9, 9, 8)
        layout.setSpacing(6)
        layout.addWidget(text("CLIPS", "section"))
        search = QLineEdit()
        search.setPlaceholderText("Suchen")
        layout.addWidget(search)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        list_body = QWidget()
        clips = QVBoxLayout(list_body)
        clips.setContentsMargins(0, 0, 2, 0)
        clips.setSpacing(2)
        for index in range(len(CLIPS)):
            row = ClipRow(index, index == self.selected_clip)
            row.chosen.connect(self.select_clip)
            clips.addWidget(row)
        clips.addStretch()
        scroll.setWidget(list_body)
        layout.addWidget(scroll, 1)
        return pane

    def build_video_tabs(self) -> QWidget:
        tabs = QWidget()
        layout = QHBoxLayout(tabs)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for index, source in enumerate(SOURCES):
            tab = button(f"{source.short}   {source.name}", "videoTabActive" if index == self.active_source else "videoTab")
            tab.clicked.connect(lambda checked=False, i=index: self.select_source(i))
            layout.addWidget(tab)
        layout.addStretch()
        return tabs

    def build_video_workspace(self, timeline_mode: str) -> QWidget:
        workspace = panel("workspace")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        title_row.addWidget(text(SOURCES[self.active_source].name, "workspaceTitle"))
        title_row.addWidget(text(f"{SOURCES[self.active_source].date}   ·   {SOURCES[self.active_source].duration}", "muted"))
        title_row.addStretch()
        title_row.addWidget(text(SOURCES[self.active_source].short, "sourceBadge"))
        layout.addLayout(title_row)
        layout.addWidget(VideoView(SOURCES[self.active_source]), 1)
        layout.addWidget(self.build_transport())
        timeline = ClipTimeline(timeline_mode, self.selected_clip)
        timeline.clip_clicked.connect(self.select_clip)
        layout.addWidget(timeline)
        layout.addWidget(self.build_marking_row())
        return workspace

    def build_transport(self) -> QWidget:
        bar = panel("transport")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(text("00:13:06.21", "time"))
        layout.addStretch()
        for value in ["−5", "◀", "▶", "▶|", "+5"]:
            layout.addWidget(button(value, "transportButton"))
        speed = QComboBox()
        speed.addItems(["0,5×", "1×", "1,5×", "2×"])
        speed.setCurrentText("1×")
        layout.addWidget(speed)
        layout.addStretch()
        layout.addWidget(text("01:18:42.00", "time"))
        return bar

    def build_marking_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        if self.pending_start:
            layout.addWidget(text(f"START  {self.pending_start}", "pending"))
            layout.addWidget(text("Press ⌘R again or set the end", "muted"))
        else:
            layout.addWidget(text("⌘R starts a new Clip", "muted"))
        layout.addStretch()
        start = button("Start gesetzt" if self.pending_start else "Start setzen", "quiet")
        start.clicked.connect(self.set_start)
        layout.addWidget(start)
        end = button("Ende setzen", "primary")
        end.setEnabled(bool(self.pending_start))
        end.clicked.connect(self.set_end)
        layout.addWidget(end)
        return row

    def editor_form(self, compact: bool = False) -> QWidget:
        form = QWidget()
        layout = QVBoxLayout(form)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        layout.addWidget(text("CLIP", "section"))
        title = QLineEdit(CLIPS[self.selected_clip].title)
        layout.addWidget(title)
        fields = QHBoxLayout()
        category = QComboBox()
        category.addItems(list(CATEGORY_COLORS))
        category.setCurrentText(CLIPS[self.selected_clip].category)
        fields.addWidget(category, 2)
        fields.addWidget(QLineEdit(CLIPS[self.selected_clip].start), 1)
        fields.addWidget(QLineEdit("00:13:20.23"), 1)
        layout.addLayout(fields)
        notes = QTextEdit(CLIPS[self.selected_clip].note)
        notes.setPlaceholderText("Beobachtung, Muster oder Hinweis für die Besprechung")
        notes.setMinimumHeight(54 if compact else 104)
        layout.addWidget(notes)
        return form

    def build_modal_editor(self) -> QWidget:
        stage = panel("modalStage")
        grid = QGridLayout(stage)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(VideoView(SOURCES[self.active_source], True), 0, 0)
        overlay = QWidget()
        outer = QVBoxLayout(overlay)
        outer.setContentsMargins(40, 30, 40, 30)
        outer.addStretch(1)
        editor = panel("editorWindow")
        editor.setMaximumWidth(860)
        editor.setMinimumWidth(720)
        content = QVBoxLayout(editor)
        content.setContentsMargins(22, 18, 22, 18)
        heading = QHBoxLayout()
        heading.addWidget(text("Neuen Clip prüfen", "editorTitle"))
        heading.addStretch()
        heading.addWidget(text(f"{SOURCES[self.active_source].short}   00:13:06.21 — 00:13:20.23", "time"))
        heading.addWidget(button("▶ Clip abspielen", "quiet"))
        content.addLayout(heading)
        content.addWidget(rule())
        columns = QHBoxLayout()
        columns.setSpacing(18)
        columns.addWidget(self.editor_form(), 3)
        goal_column = QVBoxLayout()
        goal_column.addWidget(text("WURFKARTE  ·  OPTIONAL", "section"))
        goal_column.addWidget(text("Klicken, um Wurfposition und Trefferpunkt zu setzen.", "micro", True))
        goal = GoalMap()
        goal.changed.connect(self.set_status)
        goal_column.addWidget(goal)
        columns.addLayout(goal_column, 2)
        content.addLayout(columns)
        actions = QHBoxLayout()
        actions.addWidget(button("Verwerfen", "quiet"))
        actions.addStretch()
        actions.addWidget(text("↵", "key"))
        save = button("Clip sichern", "primary")
        save.clicked.connect(self.save_editor)
        actions.addWidget(save)
        content.addLayout(actions)
        outer.addWidget(editor, 0, Qt.AlignHCenter)
        outer.addStretch(2)
        grid.addWidget(overlay, 0, 0)
        return stage

    def build_dock_editor(self) -> QWidget:
        dock = panel("editorDock")
        dock.setMinimumHeight(202)
        layout = QHBoxLayout(dock)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(18)
        layout.addWidget(self.editor_form(compact=True), 3)
        layout.addWidget(rule(True))
        goal_column = QVBoxLayout()
        goal_column.addWidget(text("WURFKARTE  ·  OPTIONAL", "section"))
        goal = GoalMap()
        goal.setMaximumHeight(132)
        goal.changed.connect(self.set_status)
        goal_column.addWidget(goal)
        layout.addLayout(goal_column, 2)
        actions = QVBoxLayout()
        actions.addWidget(button("Clip wiederholen", "quiet"))
        actions.addWidget(QCheckBox("In Schleife"))
        actions.addStretch()
        actions.addWidget(button("Abbrechen", "quiet"))
        save = button("Clip sichern", "primary")
        save.clicked.connect(self.save_editor)
        actions.addWidget(save)
        layout.addLayout(actions)
        return dock

    def build_full_editor(self) -> QWidget:
        page = panel("workspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)
        header = QHBoxLayout()
        header.addWidget(text("CLIP BEARBEITEN", "section"))
        header.addWidget(text("Wiedergabe pausiert bei 00:13:20.23", "muted"))
        header.addStretch()
        header.addWidget(button("Zurück zum Video", "quiet"))
        layout.addLayout(header)
        layout.addWidget(rule())
        columns = QHBoxLayout()
        columns.setSpacing(16)
        preview_column = QVBoxLayout()
        preview_column.addWidget(VideoView(SOURCES[self.active_source], True), 1)
        preview_column.addWidget(self.build_transport())
        preview_column.addWidget(text("Use the frame to verify exact boundaries before saving.", "micro"))
        columns.addLayout(preview_column, 5)
        form_panel = panel("editorPage")
        form_panel.setMaximumWidth(480)
        form = QVBoxLayout(form_panel)
        form.setContentsMargins(16, 14, 16, 14)
        form.addWidget(text("Clip details", "editorTitle"))
        form.addWidget(self.editor_form())
        form.addWidget(text("WURFKARTE  ·  OPTIONAL", "section"))
        goal = GoalMap()
        goal.changed.connect(self.set_status)
        form.addWidget(goal)
        actions = QHBoxLayout()
        actions.addWidget(button("Löschen", "danger"))
        actions.addStretch()
        actions.addWidget(button("Abbrechen", "quiet"))
        save = button("Änderungen sichern", "primary")
        save.clicked.connect(self.save_editor)
        actions.addWidget(save)
        form.addLayout(actions)
        columns.addWidget(form_panel, 3)
        layout.addLayout(columns, 1)
        return page

    def select_clip(self, index: int):
        self.selected_clip = index
        self.active_source = CLIPS[index].source
        self.status = f"{CLIPS[index].start}  ·  {CLIPS[index].title}  ·  {SOURCES[self.active_source].short}"
        self.render()

    def select_source(self, index: int):
        if self.pending_start and index != self.active_source:
            answer = QMessageBox.question(self, "Pending Clip", "Discard the Pending Clip and switch Source video?", QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel)
            if answer != QMessageBox.Discard:
                return
            self.pending_start = None
        self.active_source = index
        self.status = f"Source video {SOURCES[index].short} selected"
        self.render()

    def set_browser_tab(self, value: str):
        self.browser_tab = value
        self.status = "Clip list" if value == "clips" else "Source-video list"
        self.render()

    def cycle_variant(self, step: int):
        values = list(self.VARIANTS)
        self.variant = values[(values.index(self.variant) + step) % len(values)]
        self.render()

    def toggle_editor(self):
        self.editor_open = not self.editor_open
        self.pending_start = None
        self.status = "Playback paused · editor opened" if self.editor_open else "Editor closed"
        self.render()

    def mark_clip(self):
        if self.pending_start:
            self.set_end()
        else:
            self.set_start()

    def set_start(self):
        self.pending_start = "00:34:06.12"
        self.status = "Clip start set"
        self.render()

    def set_end(self):
        if not self.pending_start:
            return
        self.pending_start = None
        self.editor_open = True
        self.status = "Playback paused · new Clip ready to review"
        self.render()

    def save_editor(self):
        self.editor_open = False
        self.status = "Clip saved · Undo available"
        self.render()

    def set_status(self, value: str):
        self.status = value
        if hasattr(self, "live_status_label"):
            self.live_status_label.setText(value)

    def keyPressEvent(self, event):  # noqa: N802
        focused = QApplication.focusWidget()
        editing = isinstance(focused, (QLineEdit, QTextEdit, QComboBox))
        if not editing and event.key() in {Qt.Key_Left, Qt.Key_Right}:
            self.cycle_variant(-1 if event.key() == Qt.Key_Left else 1)
            return
        super().keyPressEvent(event)

    def capture(self, filename: str):
        QApplication.processEvents()
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        if not self.grab().save(str(CAPTURE_DIR / filename)):
            raise RuntimeError(f"Could not save {filename}")


STYLE = f"""
* {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 12px; color: {TEXT}; }}
QMainWindow {{ background: {BG}; }}
QWidget {{ background: transparent; }}
QMenuBar {{ background: #25272A; padding: 1px; border-bottom: 1px solid {LINE}; }}
QMenuBar::item {{ padding: 4px 8px; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: #3A3D42; }}
QMenu {{ background: #292C30; border: 1px solid #4A4D52; }}
QFrame[role='header'] {{ background: #24272A; border-bottom: 1px solid {LINE}; }}
QFrame[role='sidebar'] {{ background: #202327; border-right: 1px solid {LINE}; }}
QFrame[role='workspace'] {{ background: {BG}; }}
QFrame[role='panel'], QFrame[role='transport'] {{ background: {SURFACE}; }}
QFrame[role='modalStage'] {{ background: #15171A; }}
QFrame[role='editorWindow'] {{ background: #272A2E; border: 1px solid #55595E; }}
QFrame[role='editorDock'] {{ background: #292C30; border-top: 1px solid #55595E; }}
QFrame[role='editorPage'] {{ background: #25282C; border-left: 1px solid #464A4F; }}
QFrame[role='rule'] {{ color: {LINE}; max-height: 1px; max-width: 1px; }}
QFrame[role='clip'], QFrame[role='clipSelected'] {{ background: #23262A; border-bottom: 1px solid #35383D; }}
QFrame[role='clipSelected'] {{ background: #30343A; border-left: 2px solid {ACCENT}; }}
QLabel[role='product'] {{ font-size: 10px; letter-spacing: 1.3px; font-weight: 700; color: #C7C9CB; }}
QLabel[role='document'], QLabel[role='workspaceTitle'] {{ font-size: 14px; font-weight: 650; }}
QLabel[role='editorTitle'] {{ font-size: 17px; font-weight: 650; }}
QLabel[role='section'] {{ font-size: 9px; letter-spacing: 1.1px; font-weight: 700; color: #B1B3B6; }}
QLabel[role='itemTitle'] {{ font-weight: 620; }}
QLabel[role='muted'], QLabel[role='micro'] {{ color: {MUTED}; }}
QLabel[role='micro'] {{ font-size: 10px; }}
QLabel[role='time'] {{ font-family: 'SF Mono', 'Consolas', monospace; color: #D2D3D4; font-size: 10px; }}
QLabel[role='unsaved'] {{ color: #C2A36B; font-size: 9px; }}
QLabel[role='status'] {{ color: #ADB0B3; font-size: 10px; }}
QLabel[role='sourceBadge'] {{ background: #35383D; border: 1px solid #4A4E53; padding: 3px 7px; }}
QLabel[role='pending'] {{ color: #BDD4EB; background: {ACCENT_SOFT}; padding: 5px 8px; font-weight: 650; }}
QLabel[role='key'] {{ background: #36393D; border: 1px solid #53575C; padding: 3px 7px; }}
QPushButton {{ background: #2C2F33; border: 1px solid #4A4D52; border-radius: 2px; padding: 6px 10px; }}
QPushButton:hover {{ background: #363A3F; border-color: #62666B; }}
QPushButton:disabled {{ color: #6F7276; background: #25282B; border-color: #36393D; }}
QPushButton[role='primary'] {{ background: {ACCENT}; color: #101820; border-color: #719BC8; font-weight: 700; }}
QPushButton[role='primary']:hover {{ background: #719BC8; }}
QPushButton[role='primary']:disabled {{ background: #303942; color: #777D83; border-color: #414950; }}
QPushButton[role='quiet'] {{ background: #292C30; border-color: #45494D; }}
QPushButton[role='danger'] {{ color: #E39A9E; border-color: #6A4448; background: #312527; }}
QPushButton[role='tab'], QPushButton[role='tabActive'] {{ border: none; border-radius: 0; border-bottom: 1px solid {LINE}; padding: 11px; background: #24272B; color: #95989B; }}
QPushButton[role='tabActive'] {{ color: {TEXT}; background: #2A2D31; border-bottom: 2px solid {ACCENT}; }}
QPushButton[role='videoRow'], QPushButton[role='videoRowActive'] {{ background: #23262A; border: none; border-bottom: 1px solid {LINE}; border-radius: 0; padding: 0; text-align: left; }}
QPushButton[role='videoRowActive'] {{ background: #30343A; border-left: 2px solid {ACCENT}; }}
QPushButton[role='videoTab'], QPushButton[role='videoTabActive'] {{ border-radius: 0; border: 1px solid {LINE}; border-right: none; background: #25282C; padding: 8px 12px; }}
QPushButton[role='videoTabActive'] {{ background: #34383D; border-bottom: 2px solid {ACCENT}; }}
QPushButton[role='transportButton'] {{ border: none; background: transparent; min-width: 34px; padding: 5px; font-size: 14px; }}
QLineEdit, QTextEdit, QComboBox {{ background: #1E2023; border: 1px solid #4A4D52; border-radius: 2px; padding: 6px 8px; selection-background-color: #496B90; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: #788A9B; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: #202327; width: 8px; }}
QScrollBar::handle:vertical {{ background: #4A4D52; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QCheckBox {{ color: #C8C9CA; spacing: 7px; }}
QFrame[role='prototype'] {{ background: #ECEDEE; border-top: 1px solid #C8CACD; }}
QLabel[role='prototypeBadge'] {{ background: #3C4147; color: white; padding: 4px 7px; font-size: 9px; font-weight: 700; }}
QLabel[role='prototypeText'] {{ color: #202326; font-weight: 650; }}
QLabel[role='prototypeState'] {{ color: #5D6267; font-size: 9px; }}
QPushButton[role='prototypeButton'] {{ background: #FAFAFA; color: #25282B; border: 1px solid #B7BABE; border-radius: 2px; padding: 5px 8px; }}
"""


def capture_all(app: QApplication, window: PrototypeWindow):
    captures = [
        ("A", False, "clips", 1440, 900, "01-a-tabbed-clips.png"),
        ("A", False, "videos", 1280, 720, "02-a-tabbed-videos-1280.png"),
        ("A", True, "clips", 1280, 720, "03-a-modal-editor-1280.png"),
        ("B", False, "clips", 1440, 900, "04-b-video-tabs.png"),
        ("B", True, "clips", 1280, 720, "05-b-editing-dock-1280.png"),
        ("C", False, "clips", 1440, 900, "06-c-source-lanes.png"),
        ("C", True, "clips", 1280, 720, "07-c-full-editor-1280.png"),
    ]
    for variant, editor, tab, width, height, filename in captures:
        window.variant = variant
        window.editor_open = editor
        window.browser_tab = tab
        window.resize(width, height)
        window.render()
        window.show()
        app.processEvents()
        window.capture(filename)
    window.variant = "C"
    window.editor_open = False
    window.browser_tab = "clips"
    window.resize(1280, 720)
    window.select_clip(7)
    app.processEvents()
    window.capture("08-timeline-selected-v2-1280.png")
    print(f"Captured {len(captures) + 1} screenshots in {CAPTURE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Throwaway restrained Video Analyse UX prototype")
    parser.add_argument("--variant", choices=list(PrototypeWindow.VARIANTS), default="A")
    parser.add_argument("--editor", action="store_true")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Video Analyse Prototype V2")
    app.setStyle("Fusion")
    window = PrototypeWindow(args.variant, args.editor)
    if args.capture:
        QTimer.singleShot(50, lambda: (capture_all(app, window), app.quit()))
        return app.exec()
    if args.smoke:
        window.set_browser_tab("videos")
        window.select_source(1)
        window.set_browser_tab("clips")
        window.set_start()
        window.set_end()
        window.save_editor()
        window.select_clip(6)
        window.cycle_variant(1)
        window.toggle_editor()
        print("Smoke transitions completed:", window.variant, window.browser_tab, window.active_source, window.editor_open)
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
