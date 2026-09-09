"""THROWAWAY PROTOTYPE — never ship this module.

Question: which of three left-sidebar workspace hierarchies makes multi-Source-video
Clip review, two-press marking, editing, and Combined export easiest to understand?
Run with: conda run -n VideoAnalyse python prototype/video_analyse_desktop/prototype.py
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QLinearGradient, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


CAPTURE_DIR = Path(__file__).parent / "screenshots"

BG = "#08111D"
SURFACE = "#0D1928"
SURFACE_2 = "#122237"
SURFACE_3 = "#18304B"
TEXT = "#F3F8FC"
MUTED = "#91A6B9"
CYAN = "#22C7F2"
CYAN_DARK = "#075F83"
DANGER = "#FF5C6C"
WARNING = "#F2B84B"
SUCCESS = "#55D6A7"


@dataclass(frozen=True)
class Source:
    name: str
    detail: str
    duration: str
    color: str
    missing: bool = False


@dataclass(frozen=True)
class Clip:
    title: str
    category: str
    source: int
    start: str
    duration: str
    note: str


SOURCES = [
    Source("TV A — Opponent B", "03.09.2026 · Halle Nord", "01:18:42", "#267DEB"),
    Source("Opponent B — TSV C", "28.08.2026 · Sportzentrum", "01:27:06", "#7C5CFC"),
    Source("SV D — Opponent B", "20.08.2026 · Archiv", "00:58:19", "#E267A5", True),
]

CATEGORY_COLORS = {
    "Angriff": "#E96D5E",
    "Abwehr": "#38B8A0",
    "Gegenstoß": "#F4B84A",
    "Rückzug": "#9881F1",
    "Überzahl": "#4AA8E8",
    "Unterzahl": "#C878E5",
    "Torwart": "#78C95B",
    "Siebenmeter": "#E28B3E",
    "Technischer Fehler": "#DD5B81",
    "Sonstiges": "#7C91A6",
}

CLIPS = [
    Clip("Kreuzung Rückraum", "Angriff", 0, "00:04:18.12", "00:11.08", "RL zieht die Abwehr, Kreis wird frei."),
    Clip("2. Welle über links", "Gegenstoß", 1, "00:09:42.03", "00:08.17", "Schneller Anwurf nach Gegentor."),
    Clip("6:0 verschiebt spät", "Abwehr", 0, "00:13:06.21", "00:14.02", "Halbrechts kommt zweimal zu spät."),
    Clip("Parade kurze Ecke", "Torwart", 2, "00:16:52.08", "00:06.10", "Quelle fehlt; Clip bleibt sichtbar."),
    Clip("Einlaufen Außen", "Angriff", 1, "00:21:14.19", "00:12.06", "Variante nach Timeout."),
    Clip("Ballverlust Mitte", "Technischer Fehler", 0, "00:27:31.04", "00:07.13", "Passweg leicht zu antizipieren."),
    Clip("Rückzug ungeordnet", "Rückzug", 2, "00:31:09.16", "00:10.04", "Zentrum bleibt offen."),
    Clip("Überzahl 4 gegen 3", "Überzahl", 1, "00:36:22.02", "00:16.14", "Breite fehlt, trotzdem klare Chance."),
    Clip("Unterzahl kompakt", "Unterzahl", 0, "00:42:48.11", "00:18.09", "Gute Blockarbeit im Zentrum."),
    Clip("Siebenmeter links", "Siebenmeter", 1, "00:49:03.07", "00:05.18", "Schütze schaut Torwart früh aus."),
    Clip("Kreis nach Sperre", "Angriff", 0, "00:53:39.22", "00:09.03", "Sperre-Absetzen als Schlüsselbild."),
    Clip("Offensive Deckung", "Abwehr", 1, "01:01:20.15", "00:13.11", "Vorziehen gegen Rückraummitte."),
    Clip("Freier Ball", "Sonstiges", 0, "01:08:55.01", "00:06.20", "Für Besprechung vormerken."),
]


DE = {
    "sources": "QUELLVIDEOS",
    "clips": "CLIPS",
    "all_sources": "Alle Quellvideos",
    "active_source": "Aktives Quellvideo",
    "search": "Clips durchsuchen …",
    "set_start": "Start setzen",
    "set_end": "Ende setzen",
    "mark_hint": "⌘R setzt den Clip-Start",
    "export": "Exportieren",
    "save": "Sichern",
    "play_clip": "Clip abspielen",
    "loop": "Wiederholen",
    "title": "Titel",
    "notes": "Notizen",
    "category": "Kategorie",
    "cancel": "Abbrechen",
    "pending": "Clip-Start gesetzt",
    "next": "Als Nächstes: Ende setzen",
    "visible": "sichtbare Clips",
    "all_categories": "Alle Kategorien",
    "manage": "Verwalten",
}

EN = {
    "sources": "SOURCE VIDEOS",
    "clips": "CLIPS",
    "all_sources": "All Source videos",
    "active_source": "Active Source video",
    "search": "Search Clips…",
    "set_start": "Set start",
    "set_end": "Set end",
    "mark_hint": "⌘R sets the Clip start",
    "export": "Export",
    "save": "Save",
    "play_clip": "Play Clip",
    "loop": "Loop",
    "title": "Title",
    "notes": "Notes",
    "category": "Category",
    "cancel": "Cancel",
    "pending": "Clip start set",
    "next": "Next: set the end",
    "visible": "visible Clips",
    "all_categories": "All Categories",
    "manage": "Manage",
}


SCENARIOS = [
    ("welcome", "01 · Welcome / Willkommen"),
    ("new", "02 · New Analysis / Neue Analyse"),
    ("populated", "03 · Populated Analysis"),
    ("pending", "04 · Pending Clip + quick editor"),
    ("editing", "05 · Detailed Clip editing"),
    ("filtered", "06 · Filtered list + timeline"),
    ("export", "07 · Combined export"),
    ("export_progress", "08 · Export states"),
    ("missing", "09 · Missing Source video"),
    ("recovery", "10 · Recovery snapshot"),
    ("remove", "11 · Remove Source video"),
    ("english", "12 · English localization"),
    ("responsive", "13 · Responsive 1280 × 720"),
]


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    widget.setWordWrap(wrap)
    return widget


def button(text: str, role: str = "secondary") -> QPushButton:
    widget = QPushButton(text)
    widget.setProperty("role", role)
    widget.setCursor(Qt.PointingHandCursor)
    return widget


def divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setProperty("role", "divider")
    return line


def frame(role: str = "panel") -> QFrame:
    widget = QFrame()
    widget.setProperty("role", role)
    return widget


class VideoCanvas(QWidget):
    """Painted fake match frame; avoids bundling or processing real media."""

    def __init__(self, title: str, missing: bool = False):
        super().__init__()
        self.title = title
        self.missing = missing
        self.setMinimumSize(480, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = QRectF(self.rect())
        gradient = QLinearGradient(0, 0, 0, bounds.height())
        gradient.setColorAt(0, QColor("#132C40"))
        gradient.setColorAt(1, QColor("#07101A"))
        painter.fillRect(bounds, gradient)

        if not self.missing:
            court = bounds.adjusted(bounds.width() * 0.11, bounds.height() * 0.15, -bounds.width() * 0.11, -bounds.height() * 0.12)
            painter.setBrush(QColor("#9B6841"))
            painter.setPen(QPen(QColor("#DDBA83"), 2))
            painter.drawRoundedRect(court, 6, 6)
            painter.drawLine(QPointF(court.center().x(), court.top()), QPointF(court.center().x(), court.bottom()))
            painter.drawEllipse(court.center(), court.height() * 0.15, court.height() * 0.15)
            for x, y, color in [(.32, .42, "#21C7F1"), (.40, .58, "#21C7F1"), (.61, .45, "#EF5B6A"), (.68, .61, "#EF5B6A")]:
                point = QPointF(court.left() + court.width() * x, court.top() + court.height() * y)
                painter.setBrush(QColor(color))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(point, 7, 7)
            painter.setPen(QColor(255, 255, 255, 90))
            painter.setFont(QFont("", 10, QFont.DemiBold))
            painter.drawText(QRectF(18, 15, bounds.width() - 36, 28), Qt.AlignLeft, self.title)
            painter.setBrush(QColor(4, 12, 20, 205))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(bounds.width() - 144, 14, 126, 36), 7, 7)
            painter.setPen(QColor(TEXT))
            painter.drawText(QRectF(bounds.width() - 134, 14, 106, 36), Qt.AlignCenter, "TVA  18  ·  16  OPP")
        else:
            painter.setPen(QPen(QColor("#526678"), 2, Qt.DashLine))
            painter.setBrush(QColor("#0C1824"))
            painter.drawRoundedRect(bounds.adjusted(40, 35, -40, -35), 12, 12)
            painter.setPen(QColor(TEXT))
            painter.setFont(QFont("", 19, QFont.DemiBold))
            painter.drawText(bounds.adjusted(20, -20, -20, 0), Qt.AlignCenter, "Quellvideo nicht gefunden")
            painter.setPen(QColor(MUTED))
            painter.setFont(QFont("", 11))
            painter.drawText(bounds.adjusted(20, 38, -20, 0), Qt.AlignCenter, "Clips und Notizen bleiben in der Analyse erhalten.")


class Timeline(QWidget):
    selected = 2
    filtered = False

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(58)
        self.setMaximumHeight(72)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = QRectF(self.rect()).adjusted(8, 13, -8, -16)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#17293B"))
        painter.drawRoundedRect(area, 5, 5)
        segments = [(.04, .08, "Angriff"), (.13, .05, "Abwehr"), (.24, .075, "Gegenstoß"), (.36, .06, "Technischer Fehler"), (.53, .09, "Überzahl"), (.69, .07, "Angriff"), (.83, .055, "Torwart")]
        for index, (start, width, category) in enumerate(segments):
            if self.filtered and category not in {"Angriff", "Abwehr"}:
                continue
            rect = QRectF(area.left() + area.width() * start, area.top() + 6, area.width() * width, area.height() - 12)
            color = QColor(CATEGORY_COLORS[category])
            color.setAlpha(235 if index == self.selected else 120)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 3, 3)
            if index == self.selected:
                painter.setPen(QPen(QColor(TEXT), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)
                painter.setPen(Qt.NoPen)
        play_x = area.left() + area.width() * .43
        painter.setPen(QPen(QColor(CYAN), 2))
        painter.drawLine(QPointF(play_x, area.top() - 4), QPointF(play_x, area.bottom() + 4))
        painter.setPen(QColor(MUTED))
        painter.setFont(QFont("", 8))
        painter.drawText(QRectF(area.left(), area.bottom() + 3, area.width(), 14), Qt.AlignLeft, "00:00")
        painter.drawText(QRectF(area.left(), area.bottom() + 3, area.width(), 14), Qt.AlignRight, "01:18:42")


class ClickableClip(QFrame):
    clicked = Signal(int)
    double_clicked = Signal(int)

    def __init__(self, clip_index: int, show_source: bool, selected: bool = False, compact: bool = False):
        super().__init__()
        self.clip_index = clip_index
        clip = CLIPS[clip_index]
        self.setMinimumHeight(43 if compact else 50)
        self.setProperty("role", "clipSelected" if selected else "clip")
        self.setCursor(Qt.PointingHandCursor)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(9, 7 if compact else 9, 8, 7 if compact else 9)
        outer.setSpacing(8)
        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setStyleSheet(f"background:{CATEGORY_COLORS[clip.category]}; border-radius:2px")
        outer.addWidget(bar)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title = label(clip.title, "clipTitle")
        text_box.addWidget(title)
        detail = f"{clip.category}  ·  {clip.start}  ·  {clip.duration}"
        if show_source:
            detail = f"{SOURCES[clip.source].name}  ·  {detail}"
        subtitle = label(detail, "tiny")
        subtitle.setToolTip(clip.note)
        text_box.addWidget(subtitle)
        outer.addLayout(text_box, 1)
        if SOURCES[clip.source].missing:
            warning = label("!", "warningBadge")
            warning.setToolTip("Quellvideo fehlt — Wiedergabe und Export sind nicht verfügbar.")
            outer.addWidget(warning)

    def mousePressEvent(self, event):  # noqa: N802
        self.clicked.emit(self.clip_index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.double_clicked.emit(self.clip_index)
        super().mouseDoubleClickEvent(event)


class PrototypeWindow(QMainWindow):
    VARIANTS = {
        "A": "Balanced workbench",
        "B": "Clip-first command",
        "C": "Category lanes",
    }

    def __init__(self, scenario: str = "populated", variant: str = "A"):
        super().__init__()
        self.variant = variant
        self.scenario = scenario
        self.language = "en" if scenario == "english" else "de"
        self.active_source = 0
        self.selected_clip = 2
        self.pending_start: str | None = "00:18:42.08" if scenario == "pending" else None
        self.filter_category = "Angriff + Abwehr" if scenario == "filtered" else "Alle Kategorien"
        self.filter_source = 0 if scenario == "filtered" else -1
        self.sidebar_collapsed = False
        self.status_message = ""
        self.export_status = "progress"
        self.setWindowTitle("Video Analyse — Desktop UX Prototype")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 680)
        self.setStyleSheet(STYLE)
        self._build_menu()
        self._build_shell()
        self._install_shortcuts()
        self.render()

    @property
    def trn(self):
        return EN if self.language == "en" else DE

    def _build_menu(self):
        if self.language == "en":
            menus = [
                ("File", ["New Analysis", "Open Analysis…", "Open Recent", "Save", "Save As…", "Add Videos…", "Export…", "Close"]),
                ("Edit", ["Undo", "Redo", "Edit Clip", "Delete"]),
                ("View", ["Toggle Sidebar", "Full Screen", "Language"]),
                ("Help", ["Keyboard Shortcuts", "About Video Analyse"]),
            ]
        else:
            menus = [
                ("Ablage", ["Neue Analyse", "Analyse öffnen …", "Zuletzt benutzt", "Sichern", "Sichern unter …", "Videos hinzufügen …", "Exportieren …", "Schließen"]),
                ("Bearbeiten", ["Rückgängig", "Wiederholen", "Clip bearbeiten", "Löschen"]),
                ("Darstellung", ["Seitenleiste ein-/ausblenden", "Vollbild", "Sprache"]),
                ("Hilfe", ["Tastaturkurzbefehle", "Über Video Analyse"]),
            ]
        self.menuBar().clear()
        for title, actions in menus:
            menu = self.menuBar().addMenu(title)
            for action_text in actions:
                if action_text in {"Zuletzt benutzt", "Sprache", "Open Recent", "Language"}:
                    sub = menu.addMenu(action_text)
                    sub.addAction("Demo")
                else:
                    action = QAction(action_text, self)
                    menu.addAction(action)
                    if "Seitenleiste" in action_text or action_text == "Toggle Sidebar":
                        action.triggered.connect(self.toggle_sidebar)
                    if action_text.startswith("Export"):
                        action.triggered.connect(lambda: self.set_scenario("export"))

    def _build_shell(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        root.addWidget(self.content, 1)
        self.prototype_bar = self._prototype_switcher()
        root.addWidget(self.prototype_bar)

    def _prototype_switcher(self) -> QWidget:
        bar = frame("prototypeBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)
        badge = label("THROWAWAY PROTOTYPE", "prototypeBadge")
        layout.addWidget(badge)
        prev_button = button("←", "prototype")
        prev_button.setFixedWidth(34)
        prev_button.clicked.connect(lambda: self.cycle_variant(-1))
        layout.addWidget(prev_button)
        self.variant_label = label("", "prototypeText")
        self.variant_label.setMinimumWidth(190)
        layout.addWidget(self.variant_label)
        next_button = button("→", "prototype")
        next_button.setFixedWidth(34)
        next_button.clicked.connect(lambda: self.cycle_variant(1))
        layout.addWidget(next_button)
        layout.addWidget(label("Scenario", "prototypeMuted"))
        self.scenario_combo = QComboBox()
        self.scenario_combo.setProperty("role", "prototype")
        for key, name in SCENARIOS:
            self.scenario_combo.addItem(name, key)
        self.scenario_combo.setCurrentIndex(next(i for i, item in enumerate(SCENARIOS) if item[0] == self.scenario))
        self.scenario_combo.currentIndexChanged.connect(lambda: self.set_scenario(self.scenario_combo.currentData()))
        layout.addWidget(self.scenario_combo, 1)
        for title, width, height in [("1440×900", 1440, 900), ("1280×720", 1280, 720)]:
            size_button = button(title, "prototype")
            size_button.clicked.connect(lambda checked=False, w=width, h=height: self.resize(w, h))
            layout.addWidget(size_button)
        lang_button = button("DE / EN", "prototype")
        lang_button.clicked.connect(self.toggle_language)
        layout.addWidget(lang_button)
        self.state_label = label("", "prototypeState")
        self.state_label.setMinimumWidth(260)
        layout.addWidget(self.state_label)
        return bar

    def _install_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.mark_clip)
        QShortcut(QKeySequence("Meta+R"), self, activated=self.mark_clip)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=lambda: self.set_scenario("export"))
        QShortcut(QKeySequence("Meta+E"), self, activated=lambda: self.set_scenario("export"))

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            old_widget = item.widget()
            if old_widget:
                old_widget.setParent(None)
                old_widget.deleteLater()

    def render(self):
        self._build_menu()
        self.clear_content()
        self.variant_label.setText(f"{self.variant} · {self.VARIANTS[self.variant]}")
        self.state_label.setText(
            f"state: {self.scenario} · {self.language.upper()} · source {self.active_source + 1} · "
            f"clip {self.selected_clip + 1} · mark {'pending' if self.pending_start else 'idle'}"
        )
        if self.scenario == "welcome":
            self.content_layout.addWidget(self.build_welcome())
        elif self.scenario == "new":
            self.content_layout.addWidget(self.build_new_analysis())
        else:
            self.content_layout.addWidget(self.build_workspace())

    def build_welcome(self) -> QWidget:
        page = frame("welcome")
        root = QHBoxLayout(page)
        root.setContentsMargins(72, 48, 72, 48)
        root.setSpacing(64)
        brand = QVBoxLayout()
        brand.addStretch(1)
        mark = label("VA", "brandMark")
        mark.setFixedSize(64, 64)
        mark.setAlignment(Qt.AlignCenter)
        brand.addWidget(mark, 0, Qt.AlignLeft)
        brand.addWidget(label("Video Analyse", "hero"))
        brand.addWidget(label("Spiel sehen. Muster erkennen.\nDas Team gezielt vorbereiten.", "welcomeLead", True))
        brand.addSpacing(12)
        new_button = button("Neue Analyse", "primary")
        new_button.clicked.connect(lambda: self.set_scenario("new"))
        brand.addWidget(new_button, 0, Qt.AlignLeft)
        open_button = button("Analyse öffnen …", "secondary")
        brand.addWidget(open_button, 0, Qt.AlignLeft)
        brand.addStretch(2)
        root.addLayout(brand, 4)

        recent = frame("raised")
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(24, 24, 24, 24)
        recent_layout.addWidget(label("ZULETZT VERWENDET", "eyebrow"))
        rows = [
            ("Opponent B · Vorbereitung", "Heute, 10:42 · 3 Quellvideos", False),
            ("TV A — Saisonauftakt", "Gestern · 1 Quellvideo", False),
            ("SV D · Rückrunde", "31.08.2026 · Quellvideo fehlt", True),
            ("Training · Gegenstoß", "28.08.2026 · 2 Quellvideos", False),
        ]
        for name, detail, missing in rows:
            row = button("", "recent")
            row.setMinimumHeight(58)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(13, 9, 13, 9)
            title = label(("⚠  " if missing else "") + name, "recentTitle")
            row_layout.addWidget(title)
            row_layout.addWidget(label(detail, "tiny"))
            row.clicked.connect(lambda checked=False: self.set_scenario("populated"))
            recent_layout.addWidget(row)
        recent_layout.addStretch(1)
        drop = frame("drop")
        drop_layout = QVBoxLayout(drop)
        drop_layout.addWidget(label("Videos oder Analyse hier ablegen", "dropText"), 0, Qt.AlignCenter)
        drop_layout.addWidget(label("Videos starten eine unbenannte Analyse", "tiny"), 0, Qt.AlignCenter)
        recent_layout.addWidget(drop)
        root.addWidget(recent, 5)
        return page

    def build_new_analysis(self) -> QWidget:
        page = frame("welcome")
        root = QVBoxLayout(page)
        root.setContentsMargins(120, 42, 120, 42)
        root.addWidget(label("Neue Analyse", "hero"), 0, Qt.AlignHCenter)
        root.addWidget(label("Ein Name, eine Startvorlage — Videos können auch später ergänzt werden.", "welcomeLead"), 0, Qt.AlignHCenter)
        root.addSpacing(18)
        card = frame("raised")
        card.setMaximumWidth(820)
        form = QVBoxLayout(card)
        form.setContentsMargins(28, 24, 28, 24)
        form.setSpacing(12)
        form.addWidget(label("NAME DER ANALYSE", "eyebrow"))
        name = QLineEdit("Opponent B · Vorbereitung")
        form.addWidget(name)
        form.addWidget(label("KATEGORIEVORLAGE", "eyebrow"))
        template = QComboBox()
        template.addItems(["Handball — Standard (10 Kategorien)", "Ohne Vorlage"])
        form.addWidget(template)
        chips = QHBoxLayout()
        for category in list(CATEGORY_COLORS)[:6]:
            chip = label("● " + category, "categoryChip")
            chip.setStyleSheet(f"color:{CATEGORY_COLORS[category]}")
            chips.addWidget(chip)
        chips.addStretch()
        form.addLayout(chips)
        form.addWidget(label("ERSTE QUELLVIDEOS", "eyebrow"))
        video_row = frame("inset")
        vr = QHBoxLayout(video_row)
        vr.addWidget(label("2 Videos ausgewählt  ·  TV_A_OPP_B.mp4  ·  OPP_B_TSV_C.mov", "body"), 1)
        vr.addWidget(button("Videos auswählen …"))
        form.addWidget(video_row)
        hint = label("Sie können diesen Schritt überspringen und mit einer leeren Analyse beginnen.", "muted")
        form.addWidget(hint)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(button("Abbrechen"))
        create = button("Analyse erstellen", "primary")
        create.clicked.connect(lambda: self.set_scenario("populated"))
        actions.addWidget(create)
        form.addLayout(actions)
        root.addWidget(card, 1, Qt.AlignHCenter)
        root.addStretch()
        return page

    def build_workspace(self) -> QWidget:
        outer = QWidget()
        root = QVBoxLayout(outer)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.build_document_header())
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        self.sidebar = self.build_sidebar()
        self.sidebar.setMinimumWidth(270)
        self.sidebar.setMaximumWidth(480)
        splitter.addWidget(self.sidebar)
        center = self.build_center()
        splitter.addWidget(center)
        sidebar_width = 390 if self.scenario in {"pending", "editing"} else (360 if self.width() >= 1400 else 320)
        splitter.setSizes([sidebar_width, max(760, self.width() - sidebar_width)])
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)
        if self.scenario in {"export_progress", "missing"}:
            root.addWidget(self.build_background_status())
        return outer

    def build_document_header(self) -> QWidget:
        header = frame("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 9, 14, 9)
        sidebar_button = button("☰", "icon")
        sidebar_button.setToolTip("Seitenleiste ein-/ausblenden")
        sidebar_button.clicked.connect(self.toggle_sidebar)
        layout.addWidget(sidebar_button)
        layout.addWidget(label("Opponent B · Vorbereitung", "documentTitle"))
        layout.addWidget(label("● Ungesichert" if self.language == "de" else "● Unsaved", "dirty"))
        layout.addStretch()
        if self.status_message:
            layout.addWidget(label(self.status_message, "success"))
        layout.addWidget(button("⌘Z", "ghost"))
        layout.addWidget(button("⌘⇧Z", "ghost"))
        save = button(self.trn["save"], "secondary")
        layout.addWidget(save)
        export_button = button(self.trn["export"], "primary")
        export_button.clicked.connect(lambda: self.set_scenario("export"))
        layout.addWidget(export_button)
        return header

    def build_sidebar(self) -> QWidget:
        if self.variant == "A":
            return self.sidebar_balanced()
        if self.variant == "B":
            return self.sidebar_clip_first()
        return self.sidebar_category_lanes()

    def sidebar_balanced(self) -> QWidget:
        sidebar = frame("sidebar")
        root = QVBoxLayout(sidebar)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(8)
        section = QHBoxLayout()
        section.addWidget(label(self.trn["sources"], "eyebrow"))
        section.addStretch()
        section.addWidget(button("＋", "icon"))
        root.addLayout(section)
        for index, source in enumerate(SOURCES):
            root.addWidget(self.source_row(index, compact=True))
        root.addSpacing(4)
        root.addWidget(divider())
        clip_title = QHBoxLayout()
        clip_title.addWidget(label(self.trn["clips"], "eyebrow"))
        clip_title.addStretch()
        clip_title.addWidget(label(str(len(self.visible_clips())), "count"))
        root.addLayout(clip_title)
        root.addWidget(self.filter_controls(horizontal=False))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        list_body = QWidget()
        clips_layout = QVBoxLayout(list_body)
        clips_layout.setContentsMargins(0, 0, 2, 0)
        clips_layout.setSpacing(5)
        for clip_index in self.visible_clips():
            clips_layout.addWidget(self.clip_row(clip_index, show_source=self.filter_source < 0))
        clips_layout.addStretch()
        scroll.setWidget(list_body)
        root.addWidget(scroll, 1)
        if self.scenario in {"pending", "editing"}:
            root.addWidget(self.build_editor(detailed=self.scenario == "editing"))
        return sidebar

    def sidebar_clip_first(self) -> QWidget:
        sidebar = frame("sidebar")
        root = QVBoxLayout(sidebar)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(8)
        root.addWidget(label(self.trn["clips"], "eyebrow"))
        root.addWidget(self.filter_controls(horizontal=False))
        summary = frame("accentInset")
        sm = QHBoxLayout(summary)
        sm.addWidget(label(f"{len(self.visible_clips())}", "summaryNumber"))
        sm.addWidget(label(self.trn["visible"] + "\n" + ("in 3 Quellvideos" if self.language == "de" else "across 3 Source videos"), "tiny"), 1)
        root.addWidget(summary)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 2, 0)
        body_layout.setSpacing(5)
        for clip_index in self.visible_clips():
            body_layout.addWidget(self.clip_row(clip_index, show_source=True, compact=True))
        body_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        if self.scenario in {"pending", "editing"}:
            root.addWidget(self.build_editor(detailed=self.scenario == "editing"))
        root.addWidget(divider())
        sources_header = QHBoxLayout()
        sources_header.addWidget(label(self.trn["sources"], "eyebrow"))
        sources_header.addStretch()
        sources_header.addWidget(button(self.trn["manage"], "ghost"))
        root.addLayout(sources_header)
        source_strip = QHBoxLayout()
        for index, source in enumerate(SOURCES):
            source_strip.addWidget(self.source_tile(index))
        root.addLayout(source_strip)
        return sidebar

    def sidebar_category_lanes(self) -> QWidget:
        sidebar = frame("sidebar")
        root = QHBoxLayout(sidebar)
        root.setContentsMargins(8, 10, 10, 10)
        root.setSpacing(8)
        rail = QVBoxLayout()
        rail.addWidget(label("VIDEO", "eyebrow"), 0, Qt.AlignHCenter)
        for index, source in enumerate(SOURCES):
            tile = button(str(index + 1) + (" !" if source.missing else ""), "sourceRailActive" if index == self.active_source else "sourceRail")
            tile.setFixedSize(52, 48)
            tile.setToolTip(source.name)
            tile.clicked.connect(lambda checked=False, i=index: self.switch_source(i))
            rail.addWidget(tile)
        rail.addWidget(button("＋", "sourceRail"))
        rail.addStretch()
        root.addLayout(rail)
        lane = QVBoxLayout()
        lane.addWidget(label("KATEGORIEN / CLIPS" if self.language == "de" else "CATEGORIES / CLIPS", "eyebrow"))
        lane.addWidget(self.filter_controls(horizontal=False))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        lanes = QVBoxLayout(body)
        lanes.setContentsMargins(0, 0, 2, 0)
        lanes.setSpacing(8)
        grouped: dict[str, list[int]] = {}
        for clip_index in self.visible_clips():
            grouped.setdefault(CLIPS[clip_index].category, []).append(clip_index)
        for category, indexes in grouped.items():
            cat_header = frame("categoryHeader")
            ch = QHBoxLayout(cat_header)
            ch.setContentsMargins(8, 6, 8, 6)
            dot = label("●", "body")
            dot.setStyleSheet(f"color:{CATEGORY_COLORS[category]}")
            ch.addWidget(dot)
            ch.addWidget(label(category, "categoryTitle"), 1)
            ch.addWidget(label(str(len(indexes)), "count"))
            lanes.addWidget(cat_header)
            for clip_index in indexes:
                lanes.addWidget(self.clip_row(clip_index, show_source=True, compact=True))
        lanes.addStretch()
        scroll.setWidget(body)
        lane.addWidget(scroll, 1)
        if self.scenario in {"pending", "editing"}:
            lane.addWidget(self.build_editor(detailed=self.scenario == "editing"))
        root.addLayout(lane, 1)
        return sidebar

    def source_row(self, index: int, compact: bool = False) -> QWidget:
        source = SOURCES[index]
        row = button("", "sourceActive" if index == self.active_source else "source")
        row.setMinimumHeight(46)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 7, 8, 7)
        thumb = QFrame()
        thumb.setFixedSize(48, 31)
        thumb.setStyleSheet(f"background:{source.color}; border-radius:5px")
        layout.addWidget(thumb)
        words = QVBoxLayout()
        words.setSpacing(1)
        words.addWidget(label(source.name, "sourceTitle"))
        detail = ("⚠ Nicht gefunden" if source.missing else source.detail) + f"  ·  {source.duration}"
        words.addWidget(label(detail, "tiny"))
        layout.addLayout(words, 1)
        layout.addWidget(label("⋯", "muted"))
        row.clicked.connect(lambda checked=False, i=index: self.switch_source(i))
        return row

    def source_tile(self, index: int) -> QWidget:
        source = SOURCES[index]
        tile = button("", "sourceTileActive" if index == self.active_source else "sourceTile")
        tile.setMinimumHeight(34)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(7, 6, 7, 6)
        title = ("⚠ " if source.missing else "") + f"{index + 1} · {source.name.split(' — ')[0]}"
        layout.addWidget(label(title, "tiny"))
        tile.clicked.connect(lambda checked=False, i=index: self.switch_source(i))
        return tile

    def filter_controls(self, horizontal: bool = False) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder) if horizontal else QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        search = QLineEdit()
        search.setPlaceholderText(self.trn["search"])
        search.setClearButtonEnabled(True)
        layout.addWidget(search)
        selects = QHBoxLayout()
        source_filter = QComboBox()
        source_filter.addItem(self.trn["all_sources"], -1)
        for index, source in enumerate(SOURCES):
            source_filter.addItem(source.name.split(" — ")[0], index)
        source_filter.setCurrentIndex(self.filter_source + 1)
        source_filter.currentIndexChanged.connect(lambda: self.set_source_filter(source_filter.currentData()))
        selects.addWidget(source_filter, 1)
        category = QComboBox()
        category.addItem(self.trn["all_categories"], "Alle Kategorien")
        for category_name in ["Angriff + Abwehr", "Angriff", "Abwehr", "Gegenstoß", "Torwart"]:
            category.addItem(category_name, category_name)
        category.setCurrentIndex(max(0, category.findData(self.filter_category)))
        category.currentIndexChanged.connect(lambda: self.set_category_filter(category.currentData()))
        selects.addWidget(category, 1)
        layout.addLayout(selects)
        return holder

    def visible_clips(self) -> list[int]:
        visible = list(range(len(CLIPS)))
        if self.filter_source >= 0:
            visible = [index for index in visible if CLIPS[index].source == self.filter_source]
        if self.filter_category == "Angriff + Abwehr":
            visible = [index for index in visible if CLIPS[index].category in {"Angriff", "Abwehr"}]
        elif self.filter_category != "Alle Kategorien":
            visible = [index for index in visible if CLIPS[index].category == self.filter_category]
        return visible

    def clip_row(self, index: int, show_source: bool, compact: bool = False) -> ClickableClip:
        row = ClickableClip(index, show_source, index == self.selected_clip, compact)
        row.clicked.connect(self.select_clip)
        row.double_clicked.connect(self.preview_clip)
        return row

    def build_editor(self, detailed: bool) -> QWidget:
        editor = frame("editor")
        editor.setMaximumHeight(390 if detailed else 300)
        layout = QVBoxLayout(editor)
        layout.setContentsMargins(12, 11, 12, 11)
        header = QHBoxLayout()
        header.addWidget(label("Clip bearbeiten" if detailed else "Neuer Clip", "sectionTitle"))
        header.addStretch()
        if detailed:
            header.addWidget(button("▶ " + self.trn["play_clip"], "ghost"))
            loop = QCheckBox(self.trn["loop"])
            loop.setChecked(True)
            header.addWidget(loop)
        layout.addLayout(header)
        title = QLineEdit("6:0 verschiebt spät" if detailed else "")
        title.setPlaceholderText(self.trn["title"])
        layout.addWidget(title)
        times = QHBoxLayout()
        start = QLineEdit("00:13:06.21" if detailed else (self.pending_start or "00:18:42.08"))
        end = QLineEdit("00:13:02.03" if detailed else "00:18:51.14")
        times.addWidget(label("IN", "eyebrow"))
        times.addWidget(button("−1f", "nudge"))
        times.addWidget(start, 1)
        times.addWidget(button("▶|", "nudge"))
        times.addWidget(label("OUT", "eyebrow"))
        times.addWidget(button("−1f", "nudge"))
        times.addWidget(end, 1)
        times.addWidget(button("▶|", "nudge"))
        layout.addLayout(times)
        if detailed:
            layout.addWidget(label("Ende muss nach dem Start bei 00:13:06.21 liegen. Der eingegebene Wert bleibt erhalten.", "validation", True))
        categories = QComboBox()
        categories.addItems(list(CATEGORY_COLORS))
        categories.setCurrentText("Abwehr")
        layout.addWidget(categories)
        if detailed:
            notes = QTextEdit("Halbrechts kommt zweimal zu spät. Sequenz für Teamsitzung wiederholen.")
            notes.setMaximumHeight(62)
            layout.addWidget(notes)
        actions = QHBoxLayout()
        actions.addWidget(button("Löschen", "dangerGhost") if detailed else button(self.trn["cancel"]))
        actions.addStretch()
        actions.addWidget(label("↵", "keycap"))
        save = button("Änderungen sichern" if detailed else "Clip sichern", "primary")
        save.setEnabled(not detailed)
        save.clicked.connect(self.save_editor)
        actions.addWidget(save)
        layout.addLayout(actions)
        return editor

    def build_center(self) -> QWidget:
        if self.scenario == "export":
            return self.build_export()
        center = frame("center")
        layout = QVBoxLayout(center)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(9)
        source = SOURCES[self.active_source]
        title_row = QHBoxLayout()
        title_row.addWidget(label(source.name, "workspaceTitle"))
        title_row.addWidget(label(source.detail, "muted"))
        title_row.addStretch()
        title_row.addWidget(label(f"{self.active_source + 1} / {len(SOURCES)}", "count"))
        layout.addLayout(title_row)
        if self.scenario == "pending":
            layout.addWidget(self.build_pending_banner())
        if self.scenario == "missing":
            self.active_source = 2
            source = SOURCES[2]
        canvas = VideoCanvas(source.name, self.scenario == "missing" or (source.missing and self.active_source == 2))
        layout.addWidget(canvas, 1)
        if self.scenario == "missing":
            relink = button("Quellvideo suchen …", "primary")
            relink.clicked.connect(self.locate_source)
            layout.addWidget(relink, 0, Qt.AlignHCenter)
        transport = QHBoxLayout()
        transport.addWidget(label("00:34:06.12", "timecode"))
        transport.addStretch()
        transport.addWidget(button("−5", "round"))
        transport.addWidget(button("▶", "play"))
        transport.addWidget(button("+5", "round"))
        speed = QComboBox()
        speed.addItems(["0,5×", "0,75×", "1×", "1,25×", "1,5×", "2×"])
        speed.setCurrentText("1×")
        transport.addWidget(speed)
        transport.addStretch()
        transport.addWidget(label("01:18:42.00", "timecode"))
        layout.addLayout(transport)
        timeline = Timeline()
        timeline.selected = self.selected_clip % 7
        timeline.filtered = self.scenario == "filtered"
        layout.addWidget(timeline)
        mark_controls = QHBoxLayout()
        hint = self.trn["next"] if self.pending_start else self.trn["mark_hint"]
        mark_controls.addWidget(label(hint, "markHint" if self.pending_start else "muted"))
        mark_controls.addStretch()
        start_button = button("✓  00:18:42.08" if self.pending_start else self.trn["set_start"], "marked" if self.pending_start else "secondary")
        start_button.clicked.connect(self.set_start)
        mark_controls.addWidget(start_button)
        end_button = button(self.trn["set_end"], "primary")
        end_button.setEnabled(bool(self.pending_start))
        end_button.clicked.connect(self.set_end)
        mark_controls.addWidget(end_button)
        layout.addLayout(mark_controls)
        if self.scenario == "recovery":
            layout.addWidget(self.build_recovery_overlay(), 0, Qt.AlignCenter)
        if self.scenario == "remove":
            layout.addWidget(self.build_remove_overlay(), 0, Qt.AlignCenter)
        return center

    def build_pending_banner(self) -> QWidget:
        banner = frame("pending")
        row = QHBoxLayout(banner)
        row.setContentsMargins(12, 8, 12, 8)
        row.addWidget(label("●", "cyan"))
        row.addWidget(label(self.trn["pending"], "sectionTitle"))
        row.addWidget(label("00:18:42.08", "timecode"))
        row.addStretch()
        row.addWidget(label(self.trn["next"], "markHint"))
        row.addWidget(label("⌘R", "keycap"))
        return banner

    def build_export(self) -> QWidget:
        page = frame("center")
        root = QHBoxLayout(page)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(18)
        ordering = frame("panel")
        left = QVBoxLayout(ordering)
        left.setContentsMargins(18, 18, 18, 18)
        left.addWidget(label("Kombinierter Export", "workspaceTitle"))
        left.addWidget(label("5 Clips · alle Quellvideos · Filter: Kategorien Angriff + Abwehr", "muted"))
        left.addWidget(label("EXPORTLISTE", "eyebrow"))
        for category, indexes in [("Angriff", [0, 4, 10]), ("Abwehr", [2, 11])]:
            heading = QHBoxLayout()
            dot = label("●", "body")
            dot.setStyleSheet(f"color:{CATEGORY_COLORS[category]}")
            heading.addWidget(dot)
            heading.addWidget(label(category, "categoryTitle"))
            heading.addStretch()
            heading.addWidget(label("Kategorieüberschrift", "tiny"))
            left.addLayout(heading)
            for position, index in enumerate(indexes, 1):
                item = frame("exportItem")
                row = QHBoxLayout(item)
                row.setContentsMargins(10, 7, 10, 7)
                row.addWidget(label("⠿", "muted"))
                row.addWidget(label(str(position), "count"))
                row.addWidget(label(CLIPS[index].title, "clipTitle"), 1)
                row.addWidget(label(SOURCES[CLIPS[index].source].name.split(" — ")[0], "tiny"))
                row.addWidget(label(CLIPS[index].duration, "timecode"))
                left.addWidget(item)
        left.addStretch()
        left.addWidget(label("Ziehen ändert nur diese Exportliste, nicht die Analyse.", "tiny"))
        root.addWidget(ordering, 3)
        settings = frame("raised")
        settings.setMaximumWidth(410)
        right = QVBoxLayout(settings)
        right.setContentsMargins(20, 20, 20, 20)
        right.addWidget(label("Darstellung", "sectionTitle"))
        for title, checked in [("Originalton", True), ("Kategorieüberschrift", True), ("Clip-Titel einblenden", False), ("Quellvideo-Namen", False), ("Notizen einblenden", False)]:
            check = QCheckBox(title)
            check.setChecked(checked)
            right.addWidget(check)
        right.addWidget(divider())
        right.addWidget(label("QUALITÄT", "eyebrow"))
        quality = QComboBox()
        quality.addItems(["Original", "1080p", "720p"])
        right.addWidget(quality)
        right.addWidget(label("ZIEL", "eyebrow"))
        destination = frame("inset")
        dr = QHBoxLayout(destination)
        dr.addWidget(label("Opponent_B_Vorbereitung.mp4", "body"), 1)
        dr.addWidget(button("Ändern …", "ghost"))
        right.addWidget(destination)
        right.addStretch()
        actions = QHBoxLayout()
        actions.addWidget(button("Abbrechen"))
        start = button("Export starten", "primary")
        start.clicked.connect(lambda: self.set_scenario("export_progress"))
        actions.addWidget(start)
        right.addLayout(actions)
        root.addWidget(settings, 2)
        return page

    def build_background_status(self) -> QWidget:
        status = frame("status")
        layout = QHBoxLayout(status)
        layout.setContentsMargins(16, 10, 16, 10)
        if self.scenario == "missing":
            layout.addWidget(label("⚠", "warning"))
            layout.addWidget(label("1 Quellvideo fehlt", "sectionTitle"))
            layout.addWidget(label("2 betroffene Clips können nicht wiedergegeben oder exportiert werden.", "muted"))
            layout.addStretch()
            action = button("Quellvideo suchen …", "secondary")
            action.clicked.connect(self.locate_source)
            layout.addWidget(action)
        elif self.export_status == "progress":
            layout.addWidget(label("EXPORT", "eyebrow"))
            layout.addWidget(label("Opponent_B_Vorbereitung.mp4", "sectionTitle"))
            progress = QSlider(Qt.Horizontal)
            progress.setValue(64)
            progress.setEnabled(False)
            progress.setMaximumWidth(260)
            layout.addWidget(progress)
            layout.addWidget(label("64 % · ca. 01:18 verbleibend", "muted"))
            layout.addStretch()
            layout.addWidget(button("Abbrechen", "dangerGhost"))
            close_button = button("Schließen simulieren", "secondary")
            close_button.clicked.connect(self.show_close_during_export)
            layout.addWidget(close_button)
            completed = button("Als abgeschlossen zeigen", "secondary")
            completed.clicked.connect(lambda: self.show_export_result("complete"))
            layout.addWidget(completed)
            failed = button("Fehler simulieren", "secondary")
            failed.clicked.connect(lambda: self.show_export_result("failed"))
            layout.addWidget(failed)
        elif self.export_status == "complete":
            layout.addWidget(label("✓", "success"))
            layout.addWidget(label("Export abgeschlossen", "sectionTitle"))
            layout.addWidget(label("Opponent_B_Vorbereitung.mp4 · 248 MB", "muted"))
            layout.addStretch()
            layout.addWidget(button("Im Finder zeigen", "primary"))
            layout.addWidget(button("Ausblenden", "ghost"))
        else:
            layout.addWidget(label("!", "dangerBadge"))
            layout.addWidget(label("Export fehlgeschlagen", "sectionTitle"))
            layout.addWidget(label("Clip 7 konnte nicht gelesen werden · Quellvideo: SV D — Opponent B", "muted"))
            layout.addStretch()
            layout.addWidget(button("Details anzeigen", "secondary"))
            layout.addWidget(button("Erneut versuchen", "primary"))
        return status

    def build_recovery_overlay(self) -> QWidget:
        panel = frame("modal")
        panel.setFixedWidth(650)
        panel.setMinimumHeight(184)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(label("Nicht gesicherte Änderungen wiederherstellen?", "workspaceTitle"))
        layout.addWidget(label("Video Analyse wurde unerwartet beendet. Eine Wiederherstellungskopie vom 09.09.2026 um 10:38 enthält 7 neuere Änderungen.", "body", True))
        info = frame("inset")
        row = QHBoxLayout(info)
        row.addWidget(label("Gesicherte Analyse\nHeute, 10:26", "muted"), 1)
        row.addWidget(label("→", "body"))
        row.addWidget(label("Wiederherstellungskopie\nHeute, 10:38 · 24 Clips", "body"), 1)
        layout.addWidget(info)
        layout.addWidget(label("Die Analyse-Datei wird erst überschrieben, wenn Sie manuell sichern.", "tiny"))
        actions = QHBoxLayout()
        actions.addWidget(button("Gesicherte Version öffnen"))
        actions.addStretch()
        actions.addWidget(button("Änderungen wiederherstellen", "primary"))
        layout.addLayout(actions)
        return panel

    def build_remove_overlay(self) -> QWidget:
        panel = frame("dangerModal")
        panel.setFixedWidth(660)
        panel.setMinimumHeight(188)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(label("Quellvideo aus der Analyse entfernen?", "workspaceTitle"))
        layout.addWidget(label("„TV A — Opponent B · 03.09.2026“ wird aus dieser Analyse entfernt. Das Originalvideo auf Ihrem Computer wird nicht gelöscht.", "body", True))
        warning = frame("dangerInset")
        wr = QHBoxLayout(warning)
        wr.addWidget(label("!", "dangerBadge"))
        wr.addWidget(label("14 Clips gehören zu diesem Quellvideo und werden ebenfalls aus der Analyse entfernt.", "dangerText", True), 1)
        layout.addWidget(warning)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel = button("Abbrechen", "primary")
        actions.addWidget(cancel)
        remove = button("Video und 14 Clips entfernen", "danger")
        remove.clicked.connect(self.remove_source)
        actions.addWidget(remove)
        layout.addLayout(actions)
        return panel

    def set_scenario(self, scenario: str):
        if not scenario:
            return
        self.scenario = scenario
        self.language = "en" if scenario == "english" else self.language
        if scenario != "missing":
            self.active_source = 0
        if scenario == "pending":
            self.pending_start = "00:18:42.08"
        else:
            self.pending_start = None
        if scenario == "filtered":
            self.filter_source = 0
            self.filter_category = "Angriff + Abwehr"
        elif scenario == "export":
            self.filter_source = -1
            self.filter_category = "Angriff + Abwehr"
        else:
            self.filter_source = -1
            self.filter_category = "Alle Kategorien"
        if scenario == "missing":
            self.active_source = 2
        if scenario == "export_progress":
            self.export_status = "progress"
        if scenario == "responsive":
            self.resize(1280, 720)
        self.scenario_combo.blockSignals(True)
        index = next(i for i, item in enumerate(SCENARIOS) if item[0] == scenario)
        self.scenario_combo.setCurrentIndex(index)
        self.scenario_combo.blockSignals(False)
        self.render()

    def cycle_variant(self, step: int):
        keys = list(self.VARIANTS)
        self.variant = keys[(keys.index(self.variant) + step) % len(keys)]
        self.render()

    def toggle_language(self):
        self.language = "en" if self.language == "de" else "de"
        self.render()

    def keyPressEvent(self, event):  # noqa: N802
        focused = QApplication.focusWidget()
        editing = isinstance(focused, (QLineEdit, QTextEdit, QComboBox))
        if not editing and event.key() in {Qt.Key_Left, Qt.Key_Right}:
            self.cycle_variant(-1 if event.key() == Qt.Key_Left else 1)
            event.accept()
            return
        super().keyPressEvent(event)

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        if hasattr(self, "sidebar"):
            self.sidebar.setVisible(not self.sidebar_collapsed)

    def switch_source(self, index: int):
        if index == self.active_source:
            return
        if self.pending_start:
            answer = QMessageBox.question(
                self,
                "Clip-Markierung verwerfen?",
                f"Der Clip-Start bei {self.pending_start} gehört zu „{SOURCES[self.active_source].name}“.\n\nMöchten Sie die Markierung verwerfen und das Quellvideo wechseln?",
                QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer != QMessageBox.Discard:
                return
            self.pending_start = None
        self.active_source = index
        self.render()

    def select_clip(self, index: int):
        self.selected_clip = index
        self.active_source = CLIPS[index].source
        self.status_message = f"Zu {CLIPS[index].start} gesprungen"
        self.render()

    def preview_clip(self, index: int):
        self.selected_clip = index
        self.active_source = CLIPS[index].source
        self.status_message = f"Clip-Vorschau · {CLIPS[index].duration}"
        self.render()

    def mark_clip(self):
        if self.pending_start:
            self.set_end()
        else:
            self.set_start()

    def set_start(self):
        self.pending_start = "00:34:06.12"
        self.scenario = "pending"
        self.render()

    def set_end(self):
        if not self.pending_start:
            return
        self.scenario = "pending"
        self.status_message = "Wiedergabe pausiert · Ende 00:34:17.04"
        self.render()

    def save_editor(self):
        self.pending_start = None
        self.scenario = "populated"
        self.status_message = "Clip gesichert · Rückgängig verfügbar"
        self.render()

    def set_source_filter(self, index: int):
        self.filter_source = index
        self.render()

    def set_category_filter(self, category: str):
        self.filter_category = category
        self.render()

    def locate_source(self):
        self.active_source = 2
        self.scenario = "populated"
        self.status_message = "Quellvideo wieder verknüpft · Identität geprüft"
        self.render()

    def remove_source(self):
        self.scenario = "populated"
        self.active_source = 1
        self.status_message = "Quellvideo und 14 Clips entfernt · Rückgängig"
        self.render()

    def show_export_result(self, result: str):
        self.export_status = result
        self.scenario = "export_progress"
        self.render()

    def show_close_during_export(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Export läuft")
        dialog.setText("Der Export ist noch nicht abgeschlossen. Was möchten Sie tun?")
        dialog.addButton("Export fortsetzen und App geöffnet lassen", QMessageBox.AcceptRole)
        dialog.addButton("Export abbrechen und schließen", QMessageBox.DestructiveRole)
        stay = dialog.addButton("Bleiben", QMessageBox.RejectRole)
        dialog.setDefaultButton(stay)
        dialog.exec()

    def capture(self, path: Path):
        QApplication.processEvents()
        pixmap = self.grab()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not pixmap.save(str(path)):
            raise RuntimeError(f"Could not save screenshot: {path}")


STYLE = f"""
* {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 12px; color: {TEXT}; }}
QMainWindow, QWidget {{ background: {BG}; }}
QMenuBar {{ background: #0B1623; padding: 2px; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {SURFACE_3}; }}
QMenu {{ background: {SURFACE_2}; border: 1px solid #29425A; }}
QFrame[role='header'] {{ background: #0B1724; border-bottom: 1px solid #21354A; }}
QFrame[role='sidebar'] {{ background: #0A1522; border-right: 1px solid #21354A; }}
QFrame[role='center'], QFrame[role='welcome'] {{ background: {BG}; }}
QFrame[role='panel'] {{ background: {SURFACE}; border: 1px solid #20354A; border-radius: 10px; }}
QFrame[role='raised'] {{ background: {SURFACE_2}; border: 1px solid #29435B; border-radius: 12px; }}
QFrame[role='inset'] {{ background: #0A1724; border: 1px solid #22384C; border-radius: 7px; }}
QFrame[role='accentInset'] {{ background: #0B2638; border: 1px solid {CYAN_DARK}; border-radius: 8px; }}
QFrame[role='editor'] {{ background: #10263A; border: 1px solid {CYAN_DARK}; border-radius: 9px; }}
QFrame[role='pending'] {{ background: #082B3D; border: 1px solid {CYAN_DARK}; border-radius: 7px; }}
QFrame[role='status'] {{ background: #0D1F31; border-top: 1px solid #29435A; }}
QFrame[role='modal'] {{ background: #14283C; border: 1px solid #3C5870; border-radius: 12px; }}
QFrame[role='dangerModal'] {{ background: #1A202C; border: 1px solid #793E49; border-radius: 12px; }}
QFrame[role='dangerInset'] {{ background: #351B25; border: 1px solid #743746; border-radius: 8px; }}
QFrame[role='drop'] {{ background: #0A1724; border: 1px dashed #46647B; border-radius: 9px; min-height: 78px; }}
QFrame[role='divider'] {{ color: #243A4D; max-height: 1px; }}
QFrame[role='clip'], QFrame[role='exportItem'] {{ background: #0D1B2A; border: 1px solid #1B3044; border-radius: 7px; }}
QFrame[role='clip']:hover {{ background: #11253A; border-color: #36536B; }}
QFrame[role='clipSelected'] {{ background: #12324A; border: 1px solid {CYAN_DARK}; border-radius: 7px; }}
QFrame[role='categoryHeader'] {{ background: #15263A; border-radius: 6px; }}
QLabel[role='hero'] {{ font-size: 30px; font-weight: 750; color: {TEXT}; }}
QLabel[role='welcomeLead'] {{ font-size: 17px; color: #AEC0CF; }}
QLabel[role='brandMark'] {{ font-size: 20px; font-weight: 800; color: #041019; background: {CYAN}; border-radius: 14px; }}
QLabel[role='documentTitle'], QLabel[role='workspaceTitle'] {{ font-size: 16px; font-weight: 700; }}
QLabel[role='sectionTitle'] {{ font-size: 13px; font-weight: 700; }}
QLabel[role='eyebrow'] {{ font-size: 10px; font-weight: 750; letter-spacing: 1px; color: #89A0B3; }}
QLabel[role='muted'], QLabel[role='tiny'] {{ color: {MUTED}; }}
QLabel[role='tiny'] {{ font-size: 10px; }}
QLabel[role='clipTitle'], QLabel[role='sourceTitle'], QLabel[role='recentTitle'], QLabel[role='categoryTitle'] {{ font-weight: 650; }}
QLabel[role='timecode'] {{ font-family: 'SF Mono', 'Consolas', monospace; color: #BFD0DD; font-size: 10px; }}
QLabel[role='dirty'] {{ color: {WARNING}; font-size: 10px; }}
QLabel[role='success'] {{ color: {SUCCESS}; }}
QLabel[role='cyan'], QLabel[role='markHint'] {{ color: {CYAN}; font-weight: 650; }}
QLabel[role='warning'], QLabel[role='warningBadge'] {{ color: {WARNING}; font-weight: 800; }}
QLabel[role='dangerBadge'], QLabel[role='dangerText'] {{ color: #FF8190; font-weight: 700; }}
QLabel[role='validation'] {{ color: #FF8995; background: #301923; border-radius: 5px; padding: 5px 7px; font-size: 10px; }}
QLabel[role='count'] {{ color: #B3C3D0; background: #1A2C3D; border-radius: 8px; padding: 2px 6px; }}
QLabel[role='summaryNumber'] {{ font-size: 24px; font-weight: 800; color: {CYAN}; }}
QLabel[role='keycap'] {{ color: #C8D4DE; background: #26394A; border: 1px solid #415568; border-radius: 4px; padding: 2px 6px; }}
QLabel[role='dropText'] {{ font-weight: 650; }}
QPushButton {{ background: {SURFACE_2}; border: 1px solid #30465B; border-radius: 6px; padding: 7px 11px; }}
QPushButton:hover {{ background: #1B334A; border-color: #4D687E; }}
QPushButton:disabled {{ color: #586B7B; background: #101D29; border-color: #263746; }}
QPushButton[role='primary'] {{ background: {CYAN}; color: #03111A; border-color: {CYAN}; font-weight: 750; }}
QPushButton[role='primary']:disabled {{ color: #637786; background: #142431; border-color: #2A3C4A; }}
QPushButton[role='primary']:hover {{ background: #62D9F7; }}
QPushButton[role='ghost'] {{ background: transparent; border: none; color: #A9BBC9; padding: 5px 7px; }}
QPushButton[role='icon'] {{ background: transparent; border: none; font-size: 16px; padding: 4px 7px; }}
QPushButton[role='danger'] {{ background: {DANGER}; color: #1B070A; border-color: {DANGER}; font-weight: 750; }}
QPushButton[role='dangerGhost'] {{ background: transparent; color: #FF7C8A; border-color: #6E3A44; }}
QPushButton[role='marked'] {{ background: #0B3A4D; color: {CYAN}; border-color: {CYAN_DARK}; font-weight: 650; }}
QPushButton[role='play'] {{ background: {CYAN}; color: #06121A; border-radius: 20px; min-width: 40px; min-height: 40px; font-size: 15px; }}
QPushButton[role='round'] {{ border-radius: 16px; min-width: 32px; min-height: 32px; padding: 0; }}
QPushButton[role='nudge'] {{ padding: 5px 6px; font-size: 9px; }}
QPushButton[role='source'], QPushButton[role='sourceActive'], QPushButton[role='recent'] {{ text-align: left; background: #0D1A28; border: 1px solid transparent; padding: 0; }}
QPushButton[role='sourceActive'] {{ background: #102B40; border-color: {CYAN_DARK}; }}
QPushButton[role='recent'] {{ background: #102032; border-bottom: 1px solid #294157; border-radius: 6px; }}
QPushButton[role='sourceTile'], QPushButton[role='sourceTileActive'] {{ padding: 0; background: #101E2C; min-width: 72px; }}
QPushButton[role='sourceTileActive'] {{ border-color: {CYAN}; background: #123048; }}
QPushButton[role='sourceRail'], QPushButton[role='sourceRailActive'] {{ padding: 0; background: #122236; }}
QPushButton[role='sourceRailActive'] {{ border-color: {CYAN}; color: {CYAN}; background: #133249; }}
QLineEdit, QTextEdit, QComboBox {{ background: #0A1724; border: 1px solid #2B4357; border-radius: 6px; padding: 7px 9px; selection-background-color: {CYAN_DARK}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {CYAN}; }}
QComboBox::drop-down {{ border: 0; width: 20px; }}
QScrollArea {{ background: transparent; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #30485C; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSplitter::handle {{ background: #22384A; }}
QCheckBox {{ spacing: 8px; padding: 4px 0; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QSlider::groove:horizontal {{ height: 5px; background: #253A4C; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {CYAN}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 0; }}
QFrame[role='prototypeBar'] {{ background: #F2F5F7; border-top: 2px solid #D7DEE3; }}
QLabel[role='prototypeBadge'] {{ color: #FFFFFF; background: #D43B4F; border-radius: 4px; padding: 4px 7px; font-size: 9px; font-weight: 800; }}
QLabel[role='prototypeText'] {{ color: #10202D; font-weight: 750; }}
QLabel[role='prototypeMuted'], QLabel[role='prototypeState'] {{ color: #526675; font-size: 10px; }}
QPushButton[role='prototype'], QComboBox[role='prototype'] {{ color: #152634; background: #FFFFFF; border: 1px solid #B8C5CE; padding: 5px 8px; }}
"""


def run_capture(app: QApplication, window: PrototypeWindow):
    captures = [
        ("welcome", "A", 1440, 900, "01-welcome-de.png"),
        ("populated", "A", 1440, 900, "02-workspace-a-1440.png"),
        ("populated", "B", 1440, 900, "03-workspace-b-1440.png"),
        ("populated", "C", 1440, 900, "04-workspace-c-1440.png"),
        ("pending", "A", 1280, 720, "05-pending-a-1280.png"),
        ("editing", "B", 1280, 720, "06-editing-b-1280.png"),
        ("filtered", "C", 1280, 720, "07-filtered-c-1280.png"),
        ("export", "A", 1440, 900, "08-export.png"),
        ("missing", "A", 1280, 720, "09-missing.png"),
        ("recovery", "A", 1280, 720, "10-recovery.png"),
        ("remove", "A", 1280, 720, "11-remove-warning.png"),
        ("english", "A", 1280, 720, "12-english-1280.png"),
    ]
    for scenario, variant, width, height, filename in captures:
        window.variant = variant
        window.language = "en" if scenario == "english" else "de"
        window.set_scenario(scenario)
        window.resize(width, height)
        window.show()
        app.processEvents()
        window.capture(CAPTURE_DIR / filename)
    window.variant = "A"
    window.language = "de"
    window.set_scenario("export_progress")
    window.resize(1280, 720)
    window.show_export_result("complete")
    app.processEvents()
    window.capture(CAPTURE_DIR / "13-export-complete.png")
    window.show_export_result("failed")
    app.processEvents()
    window.capture(CAPTURE_DIR / "14-export-failed.png")
    print(f"Captured {len(captures) + 2} screenshots in {CAPTURE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Throwaway Video Analyse desktop UX prototype")
    parser.add_argument("--scenario", choices=[item[0] for item in SCENARIOS], default="populated")
    parser.add_argument("--variant", choices=list(PrototypeWindow.VARIANTS), default="A")
    parser.add_argument("--capture", action="store_true", help="Capture representative states and exit")
    parser.add_argument("--smoke", action="store_true", help="Exercise state transitions without showing a long-running window")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Video Analyse Prototype")
    app.setStyle("Fusion")
    window = PrototypeWindow(args.scenario, args.variant)
    if args.capture:
        QTimer.singleShot(50, lambda: (run_capture(app, window), app.quit()))
        return app.exec()
    if args.smoke:
        window.set_start()
        window.set_end()
        window.save_editor()
        window.set_source_filter(1)
        window.set_category_filter("Angriff")
        window.cycle_variant(1)
        window.toggle_language()
        window.set_scenario("export")
        window.set_scenario("missing")
        print("Smoke transitions completed:", window.variant, window.scenario, window.language)
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
