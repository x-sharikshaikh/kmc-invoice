# app/pdf/table_layout.py
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

# Column widths (in mm) to match the reference invoice; Description absorbs remainder
COL_W_SL = 12 * mm
COL_W_QTY = 18 * mm
COL_W_RATE = 24 * mm
COL_W_AMOUNT = 26 * mm

# Grid styling to match reference invoice
W_GRID    = 0.60  # slightly thicker grid lines for better visibility
W_OUTLINE = W_GRID  # outline matches grid
W_HEAVY   = 0.80  # header/total separators slightly thicker

# Row height to match reference invoice
BODY_ROW_H = 6 * mm  # Slightly taller rows for better readability

PADDING_V = (4, 4)   # top, bottom (better spacing)
PADDING_H = (6, 6)   # left, right (better spacing)

def _col_widths(content_width: float) -> list[float]:
    fixed = COL_W_SL + COL_W_QTY + COL_W_RATE + COL_W_AMOUNT
    # Ensure Description gets at least a practical minimum; use the remainder for exact fit
    desc = max(120.0, content_width - fixed)
    return [
        COL_W_SL,
        desc,
        COL_W_QTY,
        COL_W_RATE,
        COL_W_AMOUNT,
    ]

def build_invoice_table(lines: list[dict], total: float, content_width: float, filler_height: float = 0.0):
    """
    Build a table that matches Reference Invoice.jpg.
    lines: list of dicts with keys sl, description, qty, rate, amount
    total: numeric total
    content_width: usable width inside margins
    """
    data = [["Sl.", "Description", "Qty", "Rate", "Amount"]]

    for row in lines:
        data.append([
            row["sl"],
            row["description"],
            f"{float(row['qty']):.2f}",
            f"{row['rate']:.2f}",
            f"{row['amount']:.2f}",
        ])

    # No filler row - keep table compact
    filler_i = None

    # Combined thank-you and total row (same line):
    #  - Thank you spans columns 0..2 (left side)
    #  - Column 3 shows "Total:" (right-aligned), column 4 shows amount (right-aligned)
    data.append(["Thank you for choosing KMC!", "", "", "Total:", f"{total:.2f}"])
    thank_total_i = len(data) - 1

    # Row heights: consistent height for all rows (no filler)
    row_heights = [BODY_ROW_H] * len(data)

    t = Table(data, colWidths=_col_widths(content_width), rowHeights=row_heights, repeatRows=1)

    ts = TableStyle()
    # Brand color for entire table (borders, grid, and text)
    BRAND = colors.HexColor("#1B1464")
    # Inner grid and outer outline
    ts.add("GRID", (0, 0), (-1, -1), W_GRID, BRAND)
    ts.add("LINEABOVE", (0, 0), (-1, 0), W_OUTLINE, BRAND)
    ts.add("LINEBELOW", (0, -1), (-1, -1), W_OUTLINE, BRAND)
    ts.add("LINEBEFORE", (0, 0), (0, -1), W_OUTLINE, BRAND)
    ts.add("LINEAFTER", (-1, 0), (-1, -1), W_OUTLINE, BRAND)

    # Header
    ts.add("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
    ts.add("FONTSIZE", (0, 0), (-1, 0), 11)  # Slightly larger header text
    ts.add("TEXTCOLOR", (0, 0), (-1, 0), BRAND)
    ts.add("ALIGN", (0, 0), (0, 0), "CENTER")   # Sl.
    ts.add("ALIGN", (2, 0), (4, 0), "CENTER")   # Qty, Rate, Amount
    ts.add("LINEBELOW", (0, 0), (-1, 0), W_HEAVY, BRAND)  # Use brand color and thicker line

    # Body (rows between header and the combined thank/total row, excluding filler if present)
    last_body_i = (filler_i - 1) if (filler_i is not None) else (thank_total_i - 1)
    if last_body_i >= 1:
        ts.add("FONTNAME", (0, 1), (-1, last_body_i), "Helvetica")
        ts.add("FONTSIZE", (0, 1), (-1, last_body_i), 10)  # Slightly larger body text
        ts.add("TEXTCOLOR", (0, 1), (-1, last_body_i), BRAND)
        ts.add("ALIGN", (0, 1), (0, last_body_i), "CENTER")  # Sl.
        ts.add("ALIGN", (2, 1), (2, last_body_i), "CENTER")  # Qty
        ts.add("ALIGN", (3, 1), (4, last_body_i), "RIGHT")   # Rate, Amount

    # Padding
    ts.add("LEFTPADDING",  (0, 0), (-1, -1), PADDING_H[0])
    ts.add("RIGHTPADDING", (0, 0), (-1, -1), PADDING_H[1])
    ts.add("TOPPADDING",   (0, 0), (-1, -1), PADDING_V[0])
    ts.add("BOTTOMPADDING",(0, 0), (-1, -1), PADDING_V[1])

    # Combined Thank you + Total row styling
    # Left side span across 0..2 and left-align; right side shows Total label and amount
    ts.add("SPAN", (0, thank_total_i), (2, thank_total_i))
    ts.add("FONTNAME", (0, thank_total_i), (0, thank_total_i), "Helvetica-Oblique")
    ts.add("FONTSIZE", (0, thank_total_i), (0, thank_total_i), 10)  # Slightly larger
    ts.add("TEXTCOLOR", (0, thank_total_i), (0, thank_total_i), BRAND)
    ts.add("ALIGN", (0, thank_total_i), (0, thank_total_i), "LEFT")

    # Right side: emphasize the total area
    ts.add("ALIGN", (3, thank_total_i), (3, thank_total_i), "RIGHT")  # "Total:" aligned to right
    ts.add("ALIGN", (4, thank_total_i), (4, thank_total_i), "RIGHT")  # amount right-aligned
    ts.add("FONTNAME", (3, thank_total_i), (4, thank_total_i), "Helvetica-Bold")
    ts.add("FONTSIZE", (3, thank_total_i), (4, thank_total_i), 13)  # Larger for emphasis
    ts.add("TEXTCOLOR", (3, thank_total_i), (4, thank_total_i), BRAND)
    ts.add("LINEABOVE", (0, thank_total_i), (-1, thank_total_i), W_HEAVY, BRAND)  # Thicker line above total

    # No filler row to hide

    # Vertically center all cells
    ts.add("VALIGN", (0, 0), (-1, -1), "MIDDLE")

    t.setStyle(ts)
    return t