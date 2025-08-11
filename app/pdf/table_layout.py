# app/pdf/table_layout.py
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

DEFAULT_NUMERIC_WIDTHS = {
    "sl": 28,      # Sl.
    "qty": 48,     # Qty
    "rate": 70,    # Rate
    "amount": 90,  # Amount
}

W_GRID    = 0.50  # inner grid
W_OUTLINE = W_GRID  # make outline match other lines (not bold)
W_HEAVY   = 1.10  # header bottom and total separator

PADDING_V = (4, 4)   # top, bottom
PADDING_H = (6, 6)   # left, right

def _col_widths(content_width: float) -> list[float]:
    fixed = (
        DEFAULT_NUMERIC_WIDTHS["sl"]
        + DEFAULT_NUMERIC_WIDTHS["qty"]
        + DEFAULT_NUMERIC_WIDTHS["rate"]
        + DEFAULT_NUMERIC_WIDTHS["amount"]
    )
    desc = max(120.0, content_width - fixed)  # Description absorbs remainder
    return [
        DEFAULT_NUMERIC_WIDTHS["sl"],
        desc,
        DEFAULT_NUMERIC_WIDTHS["qty"],
        DEFAULT_NUMERIC_WIDTHS["rate"],
        DEFAULT_NUMERIC_WIDTHS["amount"],
    ]

def build_invoice_table(lines: list[dict], total: float, content_width: float):
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
            row["qty"],
            f"{row['rate']:.2f}",
            f"{row['amount']:.2f}",
        ])

    # Combined thank-you and total row (same line):
    #  - Thank you spans columns 0..2 (left side)
    #  - Column 3 shows "Total:" (right-aligned), column 4 shows amount (right-aligned)
    data.append(["Thank you for choosing KMC!", "", "", "Total:", f"{total:.2f}"])
    thank_total_i = len(data) - 1

    t = Table(data, colWidths=_col_widths(content_width), repeatRows=1)

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
    ts.add("LINEBELOW", (0, 0), (-1, 0), W_HEAVY, colors.black)

    # Body (rows between header and the combined thank/total row)
    last_body_i = thank_total_i - 1
    if last_body_i >= 1:
        ts.add("FONTSIZE", (0, 1), (-1, last_body_i), 9)
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
    ts.add("FONTSIZE", (0, thank_total_i), (0, thank_total_i), 9)
    ts.add("ALIGN", (0, thank_total_i), (0, thank_total_i), "LEFT")

    # Right side: emphasize the total area
    ts.add("ALIGN", (3, thank_total_i), (3, thank_total_i), "RIGHT")  # "Total:" aligned to right
    ts.add("ALIGN", (4, thank_total_i), (4, thank_total_i), "RIGHT")  # amount right-aligned
    ts.add("FONTNAME", (3, thank_total_i), (4, thank_total_i), "Helvetica-Bold")
    ts.add("FONTSIZE", (3, thank_total_i), (4, thank_total_i), 12)
    ts.add("LINEABOVE", (0, thank_total_i), (-1, thank_total_i), W_HEAVY, colors.black)

    t.setStyle(ts)
    return t