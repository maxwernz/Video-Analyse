"""THROWAWAY PROTOTYPE A -- the one stylesheet, generated from the tokens.

Every colour, metric and radius below comes from ``tokens``. No widget in this
prototype carries an ad-hoc ``setStyleSheet`` call: if something needs to look
different it gets a selector here or a dynamic property that this sheet keys
off. That single-source rule is one of the things the prototype is testing,
because per-widget styling is how the shipped interface drifted.
"""

from __future__ import annotations

from . import fonts, tokens

_SHEET = """
QWidget {{
    background: {app};
    color: {text};
    font-family: "{ui_family}";
    font-size: {body}px;
}}

QMainWindow, QMainWindow > QWidget {{ background: {app}; }}

/* ---------- panes ---------- */

#Toolbar {{
    background: {app};
    border-bottom: {border}px solid {rule};
}}
#Sidebar {{
    background: {panel};
    border-right: {border}px solid {rule};
}}
#Editor {{
    background: {panel};
    border-left: {border}px solid {rule};
}}
#Transport {{
    background: {app};
    border-top: {border}px solid {rule};
}}
#StageHost {{ background: {stage}; }}

QSplitter::handle {{ background: {rule}; width: {border}px; }}

/* ---------- text roles ---------- */

QLabel[role="documentTitle"] {{
    font-size: {document_title}px;
    font-weight: {medium};
    color: {text};
}}
QLabel[role="section"] {{
    font-size: {section_label}px;
    font-weight: {medium};
    color: {text_muted};
    background: transparent;
}}
QLabel[role="muted"] {{ color: {text_muted}; background: transparent; }}
QLabel[role="faint"] {{ color: {text_faint}; background: transparent; }}
QLabel[role="timecode"] {{
    font-family: "{mono_family}";
    font-size: {timecode}px;
    font-weight: {medium};
    color: {text};
    background: transparent;
}}
QLabel[role="timecodeMuted"] {{
    font-family: "{mono_family}";
    font-size: {timecode}px;
    color: {text_muted};
    background: transparent;
}}
QLabel {{ background: transparent; }}

/* ---------- buttons ---------- */

QPushButton {{
    background: {control};
    border: {border}px solid {control_border};
    border-radius: {radius}px;
    color: {text};
    min-height: {control_height}px;
    padding: 0 12px;
}}
QPushButton:hover {{ background: {control_hover}; }}
QPushButton:pressed {{ background: {control_disabled}; }}
QPushButton:disabled {{
    background: {control_disabled};
    color: {text_faint};
    border-color: {rule};
}}

QPushButton[kind="primary"] {{
    background: {accent};
    border-color: {accent};
    color: {accent_on};
    font-weight: {medium};
}}
QPushButton[kind="primary"]:hover {{
    background: {accent_hover};
    border-color: {accent_hover};
}}
QPushButton[kind="primary"]:pressed {{
    background: {accent_pressed};
    border-color: {accent_pressed};
}}

/* The quiet secondary: no fill, no border, until it is pointed at. */
QPushButton[kind="quiet"] {{
    background: transparent;
    border-color: transparent;
    color: {text_muted};
}}
QPushButton[kind="quiet"]:hover {{
    background: {control};
    border-color: {control_border};
    color: {text};
}}

/* Icon-only chrome buttons in the toolbar and transport. */
QToolButton {{
    background: transparent;
    border: {border}px solid transparent;
    border-radius: {radius}px;
    color: {text};
    padding: 0;
}}
QToolButton:hover {{ background: {control_hover}; }}
QToolButton:pressed {{ background: {control}; }}
QToolButton:checked {{ background: {control}; border-color: {control_border}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

/* ---------- segmented control (Clips / Videos) ---------- */

QPushButton[segment] {{
    background: {control};
    border: {border}px solid {control_border};
    color: {text_muted};
    font-weight: {medium};
    min-height: {control_height}px;
    padding: 0 14px;
}}
QPushButton[segment="left"] {{
    border-top-left-radius: {radius}px;
    border-bottom-left-radius: {radius}px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    border-right: none;
}}
QPushButton[segment="right"] {{
    border-top-right-radius: {radius}px;
    border-bottom-right-radius: {radius}px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
}}
QPushButton[segment]:hover {{ background: {control_hover}; color: {text}; }}
QPushButton[segment]:checked {{
    background: {selection};
    border-color: {accent};
    color: {text};
}}

/* ---------- fields ---------- */

QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {control};
    border: {border}px solid {control_border};
    border-radius: {radius}px;
    color: {text};
    selection-background-color: {accent};
    selection-color: {accent_on};
    padding: 0 8px;
    min-height: {control_height}px;
}}
QTextEdit, QPlainTextEdit {{ padding: 6px 8px; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {accent}; }}
QLineEdit:disabled {{ background: {control_disabled}; color: {text_faint}; }}
QLineEdit[role="timecode"] {{
    font-family: "{mono_family}";
    font-size: {timecode}px;
    font-weight: {medium};
}}

/* ---------- clip list ---------- */

QTreeView {{
    background: {panel};
    border: none;
    outline: none;
    show-decoration-selected: 0;
}}
QTreeView::item {{ border: none; }}
QTreeView::branch {{ background: {panel}; }}

/* ---------- scrollbars: the shipped interface left these stock ---------- */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {control_border};
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {text_faint}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; background: none; border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {control_border};
    border-radius: 5px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{ background: {text_faint}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; background: none; border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* ---------- menus: the playback-speed menu and the native menu bar ---------- */

QMenu {{
    background: {panel};
    border: {border}px solid {control_border};
    border-radius: {radius}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 28px 5px 12px;
    border-radius: {radius}px;
    color: {text};
}}
QMenu::item:selected {{ background: {selection}; color: {text}; }}
QMenu::item:disabled {{ color: {text_faint}; }}
QMenu::separator {{ height: {border}px; background: {rule}; margin: 4px 8px; }}
QMenu::indicator {{ width: 0; height: 0; }}

QToolTip {{
    background: {panel};
    border: {border}px solid {control_border};
    color: {text};
    padding: 3px 6px;
}}

/* ---------- separators ---------- */

QFrame[role="rule"] {{ background: {rule}; border: none; max-height: {border}px; }}
QFrame[role="ruleVertical"] {{ background: {rule}; border: none; max-width: {border}px; }}
"""


def stylesheet() -> str:
    return _SHEET.format(
        app=tokens.APP,
        panel=tokens.PANEL,
        stage=tokens.STAGE,
        rule=tokens.RULE,
        control=tokens.CONTROL,
        control_hover=tokens.CONTROL_HOVER,
        control_border=tokens.CONTROL_BORDER,
        control_disabled=tokens.CONTROL_DISABLED,
        text=tokens.TEXT,
        text_muted=tokens.TEXT_MUTED,
        text_faint=tokens.TEXT_FAINT,
        accent=tokens.ACCENT,
        accent_hover=tokens.ACCENT_HOVER,
        accent_pressed=tokens.ACCENT_PRESSED,
        accent_on=tokens.ACCENT_ON,
        selection=tokens.SELECTION,
        radius=tokens.RADIUS,
        border=tokens.BORDER,
        control_height=tokens.CONTROL_HEIGHT,
        body=tokens.SIZE_BODY,
        document_title=tokens.SIZE_DOCUMENT_TITLE,
        section_label=tokens.SIZE_SECTION_LABEL,
        timecode=tokens.SIZE_TIMECODE,
        medium=tokens.WEIGHT_MEDIUM,
        ui_family=fonts.ui_family(),
        mono_family=fonts.mono_family(),
    )
