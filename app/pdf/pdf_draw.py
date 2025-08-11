from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.core.paths import resource_path
from app.core.currency import round_money, fmt_money
from app.pdf.table_layout import build_invoice_table


# ===== Layout constants (tweak here) =====
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE

# Margins
MARGIN_LEFT = 15 * mm
MARGIN_RIGHT = 15 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 18 * mm

# Header
HEADER_HEIGHT = 10 * mm 
LOGO_WIDTH = 36 * mm
LOGO_HEIGHT = 24 * mm
TITLE_FONT_SIZE = 25
# Typography ratios for alignment
# - Approximate ascent fraction of font size above baseline (Helvetica/NotoSans)
TITLE_ASCENT_RATIO = 0.72
# - Approximate cap height fraction of font size (capital letter height / font size)
TITLE_CAP_RATIO = 0.70

# - Target proportion: make the INVOICE text height match the logo height for visual parity
TITLE_TO_LOGO_RATIO = 0.30
LABEL_FONT_SIZE = 10
TEXT_FONT_SIZE = 10
SMALL_FONT_SIZE = 9
OWNER_FONT_SIZE = 12
PHONE_FONT_SIZE = 10

# Table columns (fit within content width = PAGE_WIDTH - margins = 180mm on A4 with 15mm margins)
# Widths sum to 180mm: 10 + 102 + 18 + 24 + 26 = 180
SL_W = 12 * mm
DESC_W = 100 * mm
QTY_W = 18 * mm
RATE_W = 24 * mm
AMT_W = 26 * mm

SL_X = MARGIN_LEFT
DESC_X = SL_X + SL_W
QTY_X = DESC_X + DESC_W
RATE_X = QTY_X + QTY_W
AMT_X = RATE_X + RATE_W

TABLE_RIGHT = AMT_X + AMT_W
ROW_HEIGHT = 6 * mm
HEADER_ROW_HEIGHT = 8 * mm
TABLE_TOP_GAP = 4 * mm  # tighter gap to match reference layout
TABLE_Y_SHIFT = 13 * mm  # move table 2 mm down from previous position

TOTALS_BLOCK_HEIGHT_MIN = 10 * mm  # smaller minimum needed for single summary row
THANK_YOU_GAP = 6 * mm
SIGN_BOX_W = 50 * mm
SIGN_BOX_H = 24 * mm
ROW_BOTTOM_GAP = 4 * mm  # minimal bottom gap beyond page margin

# Colors (print-friendly)
TEXT_COLOR = colors.black
RULE_COLOR = colors.black           # for outer borders, header rules, totals box
GRID_COLOR = colors.Color(0.6, 0.6, 0.6)  # medium gray for internal grid lines

# Footer shifts
FOOTER_SHIFT = 10 * mm            # move left footer text block up by 5 mm (from 15 to 10)
SIGN_BOX_EXTRA_SHIFT = 0 * mm     # move signatory box up by 5 mm (remove extra shift)


# ===== Helpers =====
def _register_fonts() -> Tuple[str, str]:
    """Return (regular_font_name, bold_font_name)."""
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    try:
        reg = resource_path("assets/fonts/NotoSans-Regular.ttf")
        bld = resource_path("assets/fonts/NotoSans-Bold.ttf")
        if reg.exists():
            pdfmetrics.registerFont(TTFont("NotoSans", str(reg)))
            regular = "NotoSans"
        if bld.exists():
            pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bld)))
            bold = "NotoSans-Bold"
    except Exception:
        # fall back to Helvetica variants
        pass
    return regular, bold


def _fmt_date(val: Any) -> str:
    # Expecting datetime.date; accept string fallback
    try:
        import datetime as _dt

        if isinstance(val, (_dt.date, _dt.datetime)):
            return val.strftime("%d-%m-%Y")
    except Exception:
        pass
    return str(val) if val is not None else ""


def _get(d: Dict[str, Any], path: str, default: Any = "") -> Any:
    cur: Any = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def _wrap_text(text: str, max_width: float, font_name: str, font_size: float) -> List[str]:
    text = (text or "").replace("\r", "")
    words = text.split()
    lines: List[str] = []
    line: List[str] = []
    width_fn = pdfmetrics.stringWidth

    for w in words:
        trial = (" ".join(line + [w])).strip()
        if width_fn(trial, font_name, font_size) <= max_width or not line:
            line.append(w)
        else:
            lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))

    # If the text has long unbroken sequences, hard-truncate per line end
    truncated: List[str] = []
    for ln in lines:
        if width_fn(ln, font_name, font_size) <= max_width:
            truncated.append(ln)
        else:
            # truncate with ellipsis
            s = ln
            while s and width_fn(s + "…", font_name, font_size) > max_width:
                s = s[:-1]
            truncated.append((s + "…") if s else ln)
    return truncated


def wrap_text(c: Canvas, text: str, max_width: float, font_name: str, font_size: float) -> List[str]:
    """Wrap text into at most two lines within max_width, truncating with ellipsis.

    Rules:
    - Prefer 1 line; allow 2 lines max.
    - If content overflows second line, hard-truncate the second line with an ellipsis.
    - If a single word exceeds max_width, truncate that word with ellipsis on the first line.
    - Returns a list of 1–2 strings.
    """
    s = (text or "").replace("\r", " ").replace("\n", " ")
    s = " ".join(s.split())  # collapse whitespace
    if not s:
        return [""]

    width = pdfmetrics.stringWidth

    def fit_line(words: List[str]) -> Tuple[str, List[str], bool]:
        # returns (line, remaining_words, overflowed)
        if not words:
            return "", [], False
        line_words: List[str] = []
        for i, w in enumerate(words):
            trial = (" ".join(line_words + [w])).strip()
            if not line_words and width(w, font_name, font_size) > max_width:
                # single long word: truncate it to fit with ellipsis
                cut = w
                while cut and width(cut + "…", font_name, font_size) > max_width:
                    cut = cut[:-1]
                return (cut + "…") if cut else "…", words[i + 1 :], True
            if width(trial, font_name, font_size) <= max_width:
                line_words.append(w)
            else:
                # overflow; keep previous line_words
                return " ".join(line_words), words[i:], True
        return " ".join(line_words), [], False

    words = s.split(" ")
    line1, rem, of1 = fit_line(words)
    if not rem:
        return [line1]

    # Build second line; if anything remains after fitting, append ellipsis and hard-trim
    line2, rem2, of2 = fit_line(rem)
    if rem2:
        t = (line2 + " …").strip()
        while t and width(t, font_name, font_size) > max_width:
            t = t[:-2] + "…" if t.endswith(" …") else t[:-1]
        return [line1, t if t else "…"]
    return [line1, line2]


def _fmt_qty(qty: float) -> str:
    """Format quantity with up to 3 decimals, no trailing zeros."""
    try:
        s = f"{float(qty):.3f}".rstrip('0').rstrip('.')
        return s if s else "0"
    except Exception:
        return str(qty)


def _line(canvas: Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
    canvas.line(x1, y1, x2, y2)


def _draw_header(c: Canvas, font: str, bold_font: str, data: Dict[str, Any], first_page: bool) -> float:
    """
    Draw the invoice header with:
    - Logo flush to the top margin on the left
    - Only the word "INVOICE" on the right, aligned to the logo's vertical centre baseline
    A thin rule is drawn below the header. Returns the y coordinate below the header.
    """
    top_y = PAGE_HEIGHT - MARGIN_TOP
    c.setLineWidth(0.5)
    c.setFillColor(TEXT_COLOR)

    # Try to resolve logo path from settings or fallback asset
    logo_path: Path | None = None
    try:
        settings = data.get("settings", {}) if isinstance(data.get("settings"), dict) else {}
        lp = settings.get("logo_path")
        if lp:
            p = Path(lp)
            if not p.exists() and isinstance(lp, str):
                rp = resource_path(lp)
                if rp.exists():
                    p = rp
            if p.exists():
                logo_path = p
        if not logo_path:
            p = resource_path("assets/logo.png")
            if p.exists():
                logo_path = p
    except Exception:
        logo_path = None

    # Position logo: flush to top margin, then move 10 mm up
    logo_x = MARGIN_LEFT
    logo_y = top_y - LOGO_HEIGHT + 10 * mm
    if logo_path and logo_path.exists():
        try:
            c.drawImage(
                str(logo_path),
                logo_x,
                logo_y,
                width=LOGO_WIDTH,
                height=LOGO_HEIGHT,
                preserveAspectRatio=True,
                mask='auto',
            )
        except Exception:
            pass

    # Set the header baseline to the vertical middle of the logo
    baseline_y = logo_y + (LOGO_HEIGHT * 0.5)

    # Draw only the word "INVOICE" right-aligned, shifted 3 mm below the logo's vertical mid baseline
    c.setFont(bold_font, TITLE_FONT_SIZE)
    c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, baseline_y - 3 * mm, "INVOICE")

    # Draw a horizontal rule below the header (full width)
    line_y = top_y - HEADER_HEIGHT
    prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
    prev_stroke = getattr(c, '_strokeColor', None)
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(1.0)
    _line(c, MARGIN_LEFT, line_y, PAGE_WIDTH - MARGIN_RIGHT, line_y)
    # Restore previous stroke settings
    if prev_w is not None:
        c.setLineWidth(prev_w)
    if prev_stroke is not None:
        c.setStrokeColor(prev_stroke)
    return line_y


def _draw_invoice_block(c: Canvas, font: str, data: Dict[str, Any], y_top: float) -> float:
    inv = data.get("invoice", {}) or {}
    number = inv.get("number", "")
    date_val = _fmt_date(inv.get("date"))

    # Two-column right-aligned block (labels and values), matching reference alignment
    # Shift 2mm to the right (remove previous 2mm inset)
    value_right_x = PAGE_WIDTH - MARGIN_RIGHT
    label_right_x = value_right_x - (32 * mm)           # label column to the left
    # Align with BILL TO’s first line (6 mm below the header line)
    y = y_top - 6 * mm
    c.setFont(font, LABEL_FONT_SIZE)
    # Invoice number row
    c.drawRightString(label_right_x, y, "Invoice No:")
    c.drawRightString(value_right_x, y, str(number))
    # Date row
    y -= 4.2 * mm
    c.drawRightString(label_right_x, y, "Date:")
    c.drawRightString(value_right_x, y, str(date_val))
    return y - 2 * mm


def _draw_bill_to(c: Canvas, font: str, data: Dict[str, Any], y_top: float) -> float:
    cust = data.get("customer", {}) if isinstance(data.get("customer"), dict) else {}
    name = cust.get("name", "")
    phone = cust.get("phone", "")
    address = cust.get("address", "")

    x = MARGIN_LEFT
    y = y_top - 6 * mm
    c.setFont(font, LABEL_FONT_SIZE)
    c.drawString(x, y, "BILL TO")
    y -= 5 * mm

    c.setFont(font, TEXT_FONT_SIZE)
    c.drawString(x, y, name)
    y -= 4.2 * mm
    if phone:
        c.drawString(x, y, phone)
        y -= 4.2 * mm
    for ln in str(address or "").splitlines():
        if not ln:
            continue
        c.drawString(x, y, ln)
        y -= 4.2 * mm
    return y - 2 * mm


def _draw_table_header(c: Canvas, font: str, bold_font: str, y_top: float) -> float:
    # This function is now deprecated - table drawing is handled by build_invoice_table
    # Return a position that accounts for the table header height
    return y_top - HEADER_ROW_HEIGHT


def _ensure_table_within_page(c: Canvas, y_cursor: float, need_height: float) -> bool:
    return (y_cursor - need_height) > (MARGIN_BOTTOM + TOTALS_BLOCK_HEIGHT_MIN)


def _draw_table_rows(c: Canvas, font: str, items: List[Dict[str, Any]], start_y: float, total_items: int | None = None) -> Tuple[float, int]:
    # This function is now deprecated - table drawing is handled by build_invoice_table
    # Return a position that accounts for the table rows height
    # Estimate height: header + rows + summary
    estimated_height = HEADER_ROW_HEIGHT + (len(items) * ROW_HEIGHT) + (2 * ROW_HEIGHT)  # +2 for thank you and total rows
    return start_y - estimated_height, len(items)


def _draw_summary(c: Canvas, font: str, bold_font: str, data: dict, y: float) -> float:
    # This function is now deprecated - table drawing is handled by build_invoice_table
    # Return a position that accounts for the summary rows height
    # Estimate height: thank you row + total row
    estimated_height = 2 * ROW_HEIGHT
    return y - estimated_height


def _draw_footer(c: Canvas, font: str, data: Dict[str, Any]) -> None:
    # Footer text block shifted by FOOTER_SHIFT; signatory box gets additional shift
    y = (MARGIN_BOTTOM - FOOTER_SHIFT) + 6
    x = MARGIN_LEFT
    biz = data.get("business", {}) if isinstance(data.get("business"), dict) else {}
    settings = data.get("settings", {}) if isinstance(data.get("settings"), dict) else {}
    permit = biz.get("permit", "") or settings.get("permit", "") or _get(data, "invoice.permit", "")
    pan = biz.get("pan", "") or settings.get("pan", "") or _get(data, "invoice.pan", "")
    cheque_to = biz.get("cheque_to", "") or settings.get("cheque_to", "") or biz.get("chequeTo", "")
    mobile = _get(data, "settings.phone", "") or _get(data, "business.phone", "")

    # Footer lines in the specified order and wording (drawn top-to-bottom)
    c.setFont(font, SMALL_FONT_SIZE)
    lines = []
    if permit:
        lines.append(f"Gujarat Gov. Permit No: {permit}")
    if pan:
        lines.append(f"PAN No: {pan}")
    if cheque_to:
        lines.append("Please issue the Cheque in the Name of:")
        lines.append(str(cheque_to).upper())
    if mobile:
        lines.append(f"Mobile No: {mobile}")

    if lines:
        gap = 11
        # Move the footer text block up by 1mm (1mm down from previous 2mm adjustment)
        y_top = (MARGIN_BOTTOM - FOOTER_SHIFT) + 6 + (1 * mm) + gap * (len(lines) - 1)
        for ln in lines:
            c.drawString(x, y_top, ln)
            y_top -= gap

    # Left footer rendered as plain lines above

    # Authorized Signatory box on right
    bx = PAGE_WIDTH - MARGIN_RIGHT - SIGN_BOX_W
    by = MARGIN_BOTTOM - FOOTER_SHIFT - SIGN_BOX_EXTRA_SHIFT
    prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
    prev_stroke = getattr(c, '_strokeColor', None)
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.7)
    c.rect(bx, by, SIGN_BOX_W, SIGN_BOX_H, stroke=1, fill=0)
    if prev_w is not None:
        c.setLineWidth(prev_w)
    if prev_stroke is not None:
        c.setStrokeColor(prev_stroke)
    # Owner name inside the signature box (centered)
    try:
        owner = _get(data, "settings.owner", "") or _get(data, "business.owner", "")
        if owner:
            c.setFont(font, SMALL_FONT_SIZE)
            c.drawCentredString(bx + SIGN_BOX_W / 2, by + SIGN_BOX_H / 2 + 5, str(owner))
    except Exception:
        pass
    c.setFont(font, SMALL_FONT_SIZE)
    c.drawCentredString(bx + SIGN_BOX_W / 2, by + 4, "Authorized Signatory")


# ===== New Table Layout Functions =====
def build_invoice_table_with_platypus(items: List[Dict[str, Any]], total: float, content_width: float, filler_height: float = 0.0) -> Table:
    """
    Build the invoice table using the new table layout system.
    This replaces the manual canvas drawing approach.
    """
    # Transform items to match the expected format
    lines = []
    for i, item in enumerate(items, 1):
        lines.append({
            "sl": f"{i}.",
            "description": str(item.get("description", "")),
            "qty": float(item.get("qty", 0) or 0),
            "rate": float(item.get("rate", 0) or 0),
            "amount": float(item.get("amount", 0) or 0)
        })
    
    return build_invoice_table(lines, total, content_width, filler_height=filler_height)


def _draw_table_with_platypus(c: Canvas, items: List[Dict[str, Any]], y_start: float, content_width: float) -> float:
    """
    Draw the invoice table using Platypus table layout.
    Uses wrapOn/drawOn to compute actual height to ensure reliable rendering.
    Returns the new y cursor (top of content after drawing the table).
    """
    # Calculate total for the summary row inside the table
    total = sum(float(item.get("amount", 0) or 0) for item in items)

    # Build the table flowable
    # Compute filler height so the table bottom aligns just above the footer area
    # Reserve a small gap above footer for aesthetics. Footer and sign box have shifts applied.
    footer_top = (MARGIN_BOTTOM - FOOTER_SHIFT - SIGN_BOX_EXTRA_SHIFT) + SIGN_BOX_H + 8
    available_height = max(0.0, (y_start - footer_top))

    # First, estimate height of the table without filler to see how much space remains
    probe_table = build_invoice_table_with_platypus(items, total, content_width, filler_height=0.0)
    _w_probe, h_probe = probe_table.wrapOn(c, content_width, PAGE_HEIGHT)
    filler = max(0.0, available_height - h_probe)

    # Build final table with filler height to extend vertical borders
    table = build_invoice_table_with_platypus(items, total, content_width, filler_height=filler)

    # Ask the table how much space it needs, then draw it starting at y_start
    # wrapOn returns the (width, height) the table will occupy
    _w, h = table.wrapOn(c, content_width, PAGE_HEIGHT)

    # If the table would run below the bottom margin, the caller's pagination
    # will move to a fresh page; here we simply draw and let higher-level logic
    # decide when to start a new page for long item lists.
    table.drawOn(c, MARGIN_LEFT, y_start - h)

    return y_start - h


# ===== Public API =====
def build_invoice_pdf(out_path: Path | str, data: Dict[str, Any]) -> None:
    """Draw a complete invoice PDF using ReportLab (A4) with pagination.

        Data shape (keys optional where noted):
    {
      "customer": {"name": str, "phone": str, "address": str},
            "invoice": {"number": str, "date": date|str},
            "items": [{"description": str, "qty": float, "rate": float, "amount": float}, ...],
            "total": float,
      "settings"?: {"logo_path"?: str},
      "business"?: {"permit"?: str, "pan"?: str, "cheque_to"?: str}
    }
    """

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    font, bold_font = _register_fonts()
    c = Canvas(str(out), pagesize=PAGE_SIZE)
    # Set author from business_name if provided in settings or business
    author = _get(data, "settings.business_name", None) or _get(data, "business.name", None) or "KMC Invoice"
    c.setAuthor(str(author))
    c.setTitle(f"Invoice {str(_get(data, 'invoice.number', ''))}")
    c.setLineWidth(0.5)
    # Set default print-friendly colors
    c.setFillColor(TEXT_COLOR)
    c.setStrokeColor(RULE_COLOR)

    items: List[Dict[str, Any]] = list(data.get("items", []) or [])

    def new_page(first_page: bool) -> float:
        y_after_header = _draw_header(c, font, bold_font, data, first_page)
        info_y = _draw_invoice_block(c, font, data, y_after_header)
        bill_y = _draw_bill_to(c, font, data, y_after_header)
        table_start_y = min(info_y, bill_y) - TABLE_TOP_GAP + TABLE_Y_SHIFT
        return _draw_table_header(c, font, bold_font, table_start_y)

    y = new_page(first_page=True)

    # Calculate content width for the table
    content_width = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

    start_index = 0
    while start_index < len(items):
        y_before = y
        # Use the new Platypus table system instead of deprecated functions
        y = _draw_table_with_platypus(c, items[start_index:], y, content_width)
        drawn = len(items[start_index:])  # All remaining items are drawn at once
        
        if drawn == 0:
            # Not enough space for even one row; start a new page
            c.showPage()
            y = new_page(first_page=False)
            continue
        start_index += drawn

        if start_index < len(items):
            # More items remain; continue on next page
            c.showPage()
            y = new_page(first_page=False)
        else:
            # Last page: totals are already included within the table.
            # Draw footer directly without forcing a page break.
            _draw_footer(c, font, data)

    c.save()
