# app/pdf/table_layout.py
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

# Column widths (in mm) to match the reference invoice; Description absorbs remainder
COL_W_SL = 12 * mm
COL_W_QTY = 16 * mm   # slightly narrower Qty
COL_W_RATE = 22 * mm  # slightly narrower Rate
COL_W_AMOUNT = 30 * mm  # wider Amount for large totals

W_GRID    = 0.50  # single border width for all lines
W_OUTLINE = W_GRID  # outline matches grid
W_HEAVY   = W_GRID  # header/total separators also match grid

# Consistent row height for even spacing (approx 6 mm)
BODY_ROW_H = 6 * mm

PADDING_V = (3, 3)   # top, bottom (tighter, reference-like)
PADDING_H = (5, 5)   # left, right (slightly tighter)

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

    # Optional filler row to stretch vertical borders down to footer top
    filler_i = None
    if filler_height and filler_height > 0:
        data.append(["", "", "", "", ""])  # empty row to fill space
        filler_i = len(data) - 1

    # Separate thank-you row directly above the total row
    data.append(["Thank you for choosing KMC!", "", "", "", ""])  # thank-you note row
    thank_i = len(data) - 1
    data.append(["", "", "", "Total:", f"{total:.2f}"])  # total row
    total_i = len(data) - 1

    # Row heights: set body/header/footer to a consistent height; filler gets dynamic height
    row_heights = [BODY_ROW_H] * len(data)
    if filler_i is not None:
        row_heights[filler_i] = max(0.0, float(filler_height))

    t = Table(data, colWidths=_col_widths(content_width), rowHeights=row_heights, repeatRows=1)

    ts = TableStyle()
    # Inner grid and outer outline
    ts.add("GRID", (0, 0), (-1, -1), W_GRID, colors.black)
    ts.add("LINEABOVE", (0, 0), (-1, 0), W_OUTLINE, colors.black)
    ts.add("LINEBELOW", (0, -1), (-1, -1), W_OUTLINE, colors.black)
    ts.add("LINEBEFORE", (0, 0), (0, -1), W_OUTLINE, colors.black)
    ts.add("LINEAFTER", (-1, 0), (-1, -1), W_OUTLINE, colors.black)

    # Header
    ts.add("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
    ts.add("FONTSIZE", (0, 0), (-1, 0), 10)
    ts.add("ALIGN", (0, 0), (0, 0), "CENTER")   # Sl.
    ts.add("ALIGN", (2, 0), (4, 0), "CENTER")   # Qty, Rate, Amount
    ts.add("LINEBELOW", (0, 0), (-1, 0), W_GRID, colors.black)

    # Body (rows between header and the combined thank/total row, excluding filler if present)
    last_body_i = (filler_i - 1) if (filler_i is not None) else (thank_i - 1)
    if last_body_i >= 1:
        ts.add("FONTNAME", (0, 1), (-1, last_body_i), "Helvetica")
        ts.add("FONTSIZE", (0, 1), (-1, last_body_i), 9)
        ts.add("ALIGN", (0, 1), (0, last_body_i), "CENTER")  # Sl.
        ts.add("ALIGN", (2, 1), (2, last_body_i), "CENTER")  # Qty
        ts.add("ALIGN", (3, 1), (4, last_body_i), "RIGHT")   # Rate, Amount

    # Padding
    ts.add("LEFTPADDING",  (0, 0), (-1, -1), PADDING_H[0])
    ts.add("RIGHTPADDING", (0, 0), (-1, -1), PADDING_H[1])
    ts.add("TOPPADDING",   (0, 0), (-1, -1), PADDING_V[0])
    ts.add("BOTTOMPADDING",(0, 0), (-1, -1), PADDING_V[1])

    # Thank-you row styling: left side spans across 0..2, slightly above the Total row
    ts.add("SPAN", (0, thank_i), (2, thank_i))
    ts.add("FONTNAME", (0, thank_i), (0, thank_i), "Helvetica-Oblique")
    ts.add("FONTSIZE", (0, thank_i), (0, thank_i), 9)
    ts.add("ALIGN", (0, thank_i), (0, thank_i), "LEFT")

    # Total row styling: emphasize total area with bold font and right alignment
    ts.add("ALIGN", (3, total_i), (3, total_i), "RIGHT")  # "Total:" right-aligned in its cell
    ts.add("ALIGN", (4, total_i), (4, total_i), "RIGHT")  # amount right-aligned
    ts.add("FONTNAME", (3, total_i), (4, total_i), "Helvetica-Bold")
    ts.add("FONTSIZE", (3, total_i), (4, total_i), 12)
    ts.add("LINEABOVE", (0, total_i), (-1, total_i), W_GRID, colors.black)

    # Hide any filler text (keep grid for vertical lines)
    if filler_i is not None:
        ts.add("TEXTCOLOR", (0, filler_i), (-1, filler_i), colors.white)

    # Vertically center all cells
    ts.add("VALIGN", (0, 0), (-1, -1), "MIDDLE")

    t.setStyle(ts)
    return t