"""The visual system of the workspace, in one place.

``docs/design/desktop-ux.md`` records the validated direction: neutral charcoal
surfaces, flat panes separated by thin rules, square or minimally rounded
controls, compact system typography, one restrained blue accent, and muted
Category colors only where they carry analytical meaning. Everything that
decides how the workspace looks lives here, so the composition above it reads
as structure rather than as color.
"""

from __future__ import annotations

from PySide6.QtGui import QColor


#: Neutral charcoal surfaces, one restrained blue accent, thin rules.
BACKGROUND = "#191B1E"
SURFACE = "#212428"
SURFACE_RAISED = "#272A2F"
SURFACE_ACTIVE = "#30343A"
RULE = "#3B3F45"
TEXT = "#F0F0EE"
TEXT_MUTED = "#A1A4A8"
ACCENT = "#5D8FC7"
ACCENT_BRIGHT = "#719BC8"
STAGE = "#101113"
ACCENT_TEXT = "#101820"

#: The chrome every control shares, so no second sheet re-invents it.
CONTROL_SURFACE = "#2C2F33"
CONTROL_BORDER = "#4A4D52"
CONTROL_HOVER = "#363A3F"
CONTROL_HOVER_BORDER = "#62666B"
CONTROL_DISABLED_SURFACE = "#25282B"
CONTROL_DISABLED_BORDER = "#36393D"
CONTROL_DISABLED_TEXT = "#6F7276"
FIELD_SURFACE = "#1E2023"
FIELD_SELECTION = "#496B90"

WORKSPACE_STYLE_SHEET = f"""
QMainWindow, QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: -apple-system, "Segoe UI", sans-serif;
    font-size: 12px;
}}
QFrame[role="header"] {{
    background-color: {SURFACE_RAISED};
    border-bottom: 1px solid {RULE};
}}
QFrame[role="pane"] {{
    background-color: {SURFACE};
}}
QFrame[role="editor"] {{
    background-color: {SURFACE};
    border-left: 1px solid {RULE};
}}
QFrame[role="stage"] {{
    background-color: {STAGE};
}}
QWidget[role="timeline"] {{
    background-color: transparent;
}}
QLabel {{
    background-color: transparent;
}}
QLabel[role="product"] {{
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.3px;
}}
QLabel[role="document"] {{
    font-size: 14px;
    font-weight: 600;
}}
QLabel[role="section"] {{
    color: {TEXT_MUTED};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.1px;
}}
QLabel[role="muted"] {{
    color: {TEXT_MUTED};
}}
QLabel[role="time"] {{
    color: {TEXT};
    font-family: "SF Mono", "Consolas", monospace;
}}
QPushButton {{
    background-color: {CONTROL_SURFACE};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 2px;
    padding: 5px 10px;
}}
QPushButton:hover {{
    background-color: {CONTROL_HOVER};
    border-color: {CONTROL_HOVER_BORDER};
}}
QPushButton:disabled {{
    background-color: {CONTROL_DISABLED_SURFACE};
    border-color: {CONTROL_DISABLED_BORDER};
    color: {CONTROL_DISABLED_TEXT};
}}
QPushButton[role="primary"] {{
    background-color: {ACCENT};
    border-color: {ACCENT_BRIGHT};
    color: {ACCENT_TEXT};
    font-weight: 700;
}}
QPushButton[role="primary"]:hover {{
    background-color: {ACCENT_BRIGHT};
}}
QPushButton[role="transport"] {{
    background-color: transparent;
    border: none;
    min-width: 34px;
    padding: 4px;
}}
QPushButton[role="transport"]:hover {{
    background-color: {SURFACE_ACTIVE};
}}
QPushButton[role="transport"]:checked {{
    background-color: {SURFACE_ACTIVE};
}}
QPushButton[role="link"] {{
    background-color: transparent;
    border: none;
    color: {ACCENT};
    padding: 4px 2px;
}}
QComboBox {{
    background-color: {FIELD_SURFACE};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 2px;
    padding: 4px 6px;
    selection-background-color: {FIELD_SELECTION};
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {RULE};
    selection-background-color: {SURFACE_ACTIVE};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: url(:/icons/chevron.down.png);
    width: 12px;
    height: 12px;
}}
QProgressBar {{
    background-color: {FIELD_SURFACE};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 2px;
    font-size: 10px;
    max-width: 120px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
}}
QTabWidget::pane {{
    background-color: {SURFACE};
    border: none;
    border-top: 1px solid {RULE};
}}
QTabBar::tab {{
    background-color: {SURFACE_RAISED};
    border: none;
    color: {TEXT_MUTED};
    font-weight: 600;
    letter-spacing: 0.6px;
    padding: 8px 14px;
}}
QTabBar::tab:selected {{
    background-color: {SURFACE};
    border-bottom: 2px solid {ACCENT};
    color: {TEXT};
}}
QTreeView {{
    background-color: {SURFACE};
    border: none;
    outline: none;
}}
QHeaderView::section {{
    background-color: {SURFACE_RAISED};
    border: none;
    border-bottom: 1px solid {RULE};
    border-right: 1px solid {RULE};
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 700;
    padding: 5px 6px;
}}
QTreeView::item {{
    border: none;
    padding: 4px 2px;
}}
QTreeView::item:hover {{
    background-color: {SURFACE_RAISED};
}}
QTreeView::item:selected, QTreeView::branch:selected {{
    background-color: {SURFACE_ACTIVE};
    color: {TEXT};
}}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {{
    border-image: none;
    image: url(:/icons/chevron.right.png);
}}
QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {{
    border-image: none;
    image: url(:/icons/chevron.down.png);
}}
QSplitter::handle {{
    background-color: {RULE};
    width: 1px;
}}
QScrollBar:vertical {{
    background-color: {SURFACE};
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background-color: {CONTROL_BORDER};
    min-height: 28px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
    width: 0;
}}
"""

#: How much color a Category is allowed to carry on a charcoal surface.
CATEGORY_SATURATION = 105
CATEGORY_BRIGHTNESS = 200


def muted_category_color(color: str) -> QColor:
    """Damp a Category color for display without touching the stored one.

    Category color is always secondary to the Category name and the selection
    treatment, so the workspace renders it muted rather than at whatever
    saturation the Category was given.
    """
    rendered = QColor(color)
    if not rendered.isValid():
        return rendered
    return QColor.fromHsv(
        rendered.hue(),
        min(rendered.saturation(), CATEGORY_SATURATION),
        min(max(rendered.value(), CATEGORY_BRIGHTNESS), 255),
    )


MESSAGE_BOX_STYLE_SHEET = f"""
QMessageBox {{
    background-color: {SURFACE};
}}
QMessageBox QLabel {{
    color: {TEXT};
}}
QMessageBox QPushButton {{
    background-color: {CONTROL_SURFACE};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 2px;
    padding: 6px 14px;
}}
QMessageBox QPushButton:hover {{
    background-color: {CONTROL_HOVER};
    border-color: {CONTROL_HOVER_BORDER};
}}
"""
