"""THROWAWAY PROTOTYPE A -- the frozen visual tokens, transcribed.

Source of truth is ``docs/design/visual-tokens.md``. This module only restates
those values so Python can consume them; it never tunes them. If a value here
disagrees with the document, the document wins.
"""

from __future__ import annotations

# Surfaces
STAGE = "#0B0C0D"
APP = "#131518"
PANEL = "#1A1D21"
RULE = "#2A2E34"
CONTROL = "#22262B"
CONTROL_HOVER = "#2C3138"
CONTROL_BORDER = "#343941"
CONTROL_DISABLED = "#1B1E22"

# Text
TEXT = "#E8EAED"
TEXT_MUTED = "#8A9099"
TEXT_FAINT = "#5E646C"

# Accent -- playhead, primary action, selection. Nothing else.
ACCENT = "#E4306B"
ACCENT_HOVER = "#F0538A"
ACCENT_PRESSED = "#C41F58"
ACCENT_ON = "#FFFFFF"
SELECTION = "#33172A"

# Category palette, fixed, in document order.
CATEGORY_PALETTE = (
    ("Rot", "#E2564A"),
    ("Orange", "#DE8241"),
    ("Bernstein", "#C9A227"),
    ("Limette", "#8FAE3C"),
    ("Gruen", "#4BA46A"),
    ("Petrol", "#3AA6A0"),
    ("Cyan", "#3E9BC4"),
    ("Blau", "#5B87D6"),
    ("Violett", "#8B7BD8"),
    ("Purpur", "#A96BC0"),
)

# Type scale: (point size, weight) -- weights are QFont numeric weights.
SIZE_DOCUMENT_TITLE = 15
SIZE_ROW_TITLE = 13
SIZE_BODY = 12
SIZE_SECTION_LABEL = 11
SIZE_TIMECODE = 12
SIZE_RULER_LABEL = 10

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500

# Spacing, metrics, shape
BASE = 4
GUTTER = 16
CONTROL_GAP = 8

TOOLBAR_HEIGHT = 44
TRANSPORT_HEIGHT = 56
TIMELINE_HEIGHT = 60
TIMELINE_RULER_HEIGHT = 16
TIMELINE_TRACK_HEIGHT = 44
CLIP_ROW_HEIGHT = 32
SIDEBAR_WIDTH = 300
SIDEBAR_MIN_WIDTH = 260
SIDEBAR_MAX_WIDTH = 420
EDITOR_WIDTH = 360
CONTROL_HEIGHT = 28
RADIUS = 3
BORDER = 1

WINDOW_MIN_WIDTH = 1440
WINDOW_MIN_HEIGHT = 900

# Icons
ICON_STROKE = 1.75
ICON_SIZE_TRANSPORT = 20
ICON_SIZE_DEFAULT = 16

# Timeline specifics named in the direction document.
RANGE_FILL_ALPHA = 0.40
RANGE_MINIMUM_WIDTH = 3
PLAYHEAD_WIDTH = 2
