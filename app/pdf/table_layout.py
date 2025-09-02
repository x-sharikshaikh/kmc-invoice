"""Invoice table layout — pixel-aligned to the provided reference image.

This module builds a single Platypus Table containing:
  - Header row: Sl., Description, Qty, Rate, Amount
  - Body rows for items
  - Optional filler row (blank) to extend the grid downwards for the long empty area
  - Bottom row combining: "Thank you for choosing KMC!" on the left, and a Total block on the right

Styling matches the reference:
  - Brand color for text and rules (#1B1464)
  - Thicker outline and header/total separators
  - Numeric alignment (Qty centered; Rate/Amount right)
  - Tight paddings for crisp alignment
"""

from typing import Any, Dict, List

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

# Brand color and uniform line weight
BRAND = colors.HexColor("#1B1464")
# Use a single stroke width for all table rules to avoid bold/different borders
W_GRID = 0.50      # all grid and separators

# Column widths (in mm) like the reference; description takes the remainder
COL_W_SL = 12 * mm
COL_W_QTY = 18 * mm
COL_W_RATE = 24 * mm
COL_W_AMOUNT = 26 * mm

# Row heights and paddings (compact, crisp)
HEADER_H = 8 * mm
BODY_H = 8 * mm
THANK_H = 7 * mm
PAD_L, PAD_R = 6, 6
PAD_T, PAD_B = 3, 3


def _col_widths(content_width: float) -> List[float]:
    fixed = COL_W_SL + COL_W_QTY + COL_W_RATE + COL_W_AMOUNT
    desc = max(100.0, float(content_width) - float(fixed))
    return [COL_W_SL, desc, COL_W_QTY, COL_W_RATE, COL_W_AMOUNT]


def _fmt2(val: Any) -> str:
    try:
        return f"{float(val):.2f}"
    except Exception:
        return "0.00"


def build_invoice_table(lines: List[Dict[str, Any]], total: float, content_width: float, filler_height: float = 0.0) -> Table:
    # Build data rows
    data: List[List[str]] = [["Sl.", "Description", "Qty", "Rate", "Amount"]]
    for row in lines:
        data.append([
            str(row.get("sl", "")),
            str(row.get("description", "")),
            _fmt2(row.get("qty", 0)),
            _fmt2(row.get("rate", 0)),
            _fmt2(row.get("amount", 0)),
        ])

    filler_i: int | None = None
    if isinstance(filler_height, (int, float)) and filler_height > 1.0:
        data.append(["", "", "", "", ""])  # blank row to extend grid
        filler_i = len(data) - 1

    # Thank-you + Total row (in-table, like the image)
    data.append(["Thank you for choosing KMC!", "", "", "Total:", _fmt2(total)])
    thank_i = len(data) - 1

    # Row heights: header + body + optional filler + thank/total
    row_heights: List[float] = []
    for r in range(len(data)):
        if r == 0:
            row_heights.append(HEADER_H)
        elif r == thank_i:
            row_heights.append(THANK_H)
        elif filler_i is not None and r == filler_i:
            row_heights.append(float(filler_height))
        else:
            row_heights.append(BODY_H)

    t = Table(data, colWidths=_col_widths(content_width), rowHeights=row_heights, repeatRows=1)

    ts = TableStyle([
        # Full grid (includes outer border) with uniform stroke
        ("GRID", (0, 0), (-1, -1), W_GRID, BRAND),

        # Header
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),      # Sl.
        ("ALIGN", (1, 0), (1, 0), "LEFT"),        # Description
        ("ALIGN", (2, 0), (4, 0), "CENTER"),      # Qty, Rate, Amount
    ("LINEBELOW", (0, 0), (-1, 0), W_GRID, BRAND),

        # Body
        ("FONTNAME", (0, 1), (-1, thank_i - 1 if filler_i is None else filler_i - 1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, thank_i - 1 if filler_i is None else filler_i - 1), 10),
        ("TEXTCOLOR", (0, 1), (-1, thank_i - 1 if filler_i is None else filler_i - 1), BRAND),
        ("ALIGN", (0, 1), (0, thank_i - 1 if filler_i is None else filler_i - 1), "CENTER"),   # Sl.
        ("ALIGN", (1, 1), (1, thank_i - 1 if filler_i is None else filler_i - 1), "LEFT"),     # Description
        ("ALIGN", (2, 1), (2, thank_i - 1 if filler_i is None else filler_i - 1), "CENTER"),   # Qty
        ("ALIGN", (3, 1), (4, thank_i - 1 if filler_i is None else filler_i - 1), "RIGHT"),    # Rate, Amount

        # Padding and vertical alignment
        ("LEFTPADDING", (0, 0), (-1, -1), PAD_L),
        ("RIGHTPADDING", (0, 0), (-1, -1), PAD_R),
        ("TOPPADDING", (0, 0), (-1, -1), PAD_T),
        ("BOTTOMPADDING", (0, 0), (-1, -1), PAD_B),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Thank-you + Total row
        ("SPAN", (0, thank_i), (2, thank_i)),
        ("FONTNAME", (0, thank_i), (0, thank_i), "Helvetica-Oblique"),
        ("FONTSIZE", (0, thank_i), (0, thank_i), 10),
        ("TEXTCOLOR", (0, thank_i), (0, thank_i), BRAND),
        ("ALIGN", (0, thank_i), (0, thank_i), "LEFT"),

        ("ALIGN", (3, thank_i), (3, thank_i), "RIGHT"),
        ("ALIGN", (4, thank_i), (4, thank_i), "RIGHT"),
        ("FONTNAME", (3, thank_i), (4, thank_i), "Helvetica-Bold"),
        ("FONTSIZE", (3, thank_i), (4, thank_i), 13),
        ("TEXTCOLOR", (3, thank_i), (4, thank_i), BRAND),
    ("LINEABOVE", (0, thank_i), (-1, thank_i), W_GRID, BRAND),
    ])

    t.setStyle(ts)
    return t