from __future__ import annotations

"""Design tokens for KMC Invoice UI.

- Keep colors calm and neutral; avoid high-contrast unless in dark mode.
- Spacing scale uses 4px multiples.
"""


class Colors:
    # Light
    bg = "#fafafa"
    card = "#ffffff"
    text = "#222"
    subtext = "#444"
    border = "#e0e0e0"
    input_border = "#cfcfcf"
    primary = "#5b8def"
    primary_hover = "#4c7ae0"

    # Dark
    bg_dark = "#2b2b2b"
    card_dark = "#2f2f2f"
    text_dark = "#f0f0f0"
    border_dark = "#3d3d3d"
    input_border_dark = "#666"
    primary_dark = "#7aa2ff"


class Radius:
    sm = 6
    md = 10
    lg = 12


class Space:
    xs = 4
    sm = 8
    md = 12
    lg = 16
    xl = 24


class Elevation:
    shadow = "0 2px 16px rgba(0,0,0,0.08)"


class Z:
    header = 10
    footer = 5


class Metrics:
    # Basic UX metrics keys
    FILE = "metrics.jsonl"
    SESSION_START = "session_start"
    SAVE_DRAFT = "save_draft"
    SAVE_PDF = "save_pdf"
    PRINT = "print"
