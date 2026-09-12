"""THROWAWAY PROTOTYPE A -- the 44px working toolbar.

A working toolbar, not a wordmark strip. The shipped interface spent its top
band on the product name; here it carries file and Analysis actions on the
left, the Analysis name and dirty state in the middle, and view controls right.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from . import controls, tokens


class Toolbar(QWidget):
    add_source_video_requested = Signal()
    sidebar_toggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toolbar")
        self.setFixedHeight(tokens.TOOLBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(tokens.CONTROL_GAP, 0, tokens.CONTROL_GAP, 0)
        layout.setSpacing(2)

        for name, tooltip in (
            ("file-plus", "Neue Analyse"),
            ("folder-open", "Analyse öffnen"),
            ("save", "Analyse speichern"),
        ):
            layout.addWidget(controls.IconButton(name, tooltip=tooltip, parent=self))

        layout.addSpacing(6)
        layout.addWidget(_separator(self))
        layout.addSpacing(6)

        add_video = controls.IconButton("video", tooltip="Video hinzufügen", parent=self)
        add_video.clicked.connect(self.add_source_video_requested.emit)
        layout.addWidget(add_video)
        layout.addWidget(
            controls.IconButton("upload", tooltip="Zusammenschnitt exportieren", parent=self)
        )

        layout.addStretch(1)

        self._title = QLabel(self)
        self._title.setProperty("role", "documentTitle")
        layout.addWidget(self._title)

        self._dirty = QLabel("•", self)
        self._dirty.setProperty("role", "faint")
        self._dirty.setToolTip("Nicht gespeicherte Änderungen")
        layout.addWidget(self._dirty)

        layout.addStretch(1)

        sidebar = controls.IconButton(
            "panel-left", tooltip="Seitenleiste ein- und ausblenden", parent=self
        )
        sidebar.clicked.connect(self.sidebar_toggled.emit)
        layout.addWidget(sidebar)
        layout.addWidget(
            controls.IconButton("maximize", tooltip="Vollbild", parent=self)
        )

    def show_analysis(self, title: str, *, dirty: bool) -> None:
        self._title.setText(title)
        self._dirty.setVisible(dirty)


def _separator(parent: QWidget) -> QFrame:
    rule = QFrame(parent)
    rule.setProperty("role", "ruleVertical")
    rule.setFixedWidth(tokens.BORDER)
    rule.setFixedHeight(20)
    return rule
