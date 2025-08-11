from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.core.paths import resource_path
from app.core.currency import round_money, fmt_money


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
SL_W = 10 * mm
DESC_W = 102 * mm
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
HEADER_ROW_HEIGHT = 7 * mm
TABLE_TOP_GAP = 8 * mm  # gap between info blocks and table header (increased for breathing room)

TOTALS_BLOCK_HEIGHT_MIN = 10 * mm  # smaller minimum needed for single summary row
THANK_YOU_GAP = 6 * mm
SIGN_BOX_W = 50 * mm
SIGN_BOX_H = 24 * mm
ROW_BOTTOM_GAP = 4 * mm  # minimal bottom gap beyond page margin

# Colors (print-friendly)
TEXT_COLOR = colors.black
RULE_COLOR = colors.black
GRID_COLOR = colors.Color(0.6, 0.6, 0.6)  # medium gray for table grid


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

    right_x = PAGE_WIDTH - MARGIN_RIGHT
    # Align with BILL TO’s first line (6 mm below the header line)
    y = y_top - 6 * mm
    c.setFont(font, LABEL_FONT_SIZE)
    c.drawRightString(right_x, y, f"Invoice No: {number}")
    y -= 4.2 * mm
    c.drawRightString(right_x, y, f"Date: {date_val}")
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
    # Column titles
    y = y_top
    c.setFont(bold_font, TEXT_FONT_SIZE)
    c.drawString(SL_X, y, "Sl.")
    c.drawString(DESC_X, y, "Description")
    # Center the Qty, Rate, Amount headings in their columns
    c.drawCentredString(QTY_X + QTY_W / 2, y, "Qty")
    c.drawCentredString(RATE_X + RATE_W / 2, y, "Rate")
    c.drawCentredString(AMT_X + AMT_W / 2, y, "Amount")

    # Header underline and outer border line start
    y -= 3
    # Draw a bolder rule for header
    hdr_prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
    hdr_prev_stroke = getattr(c, '_strokeColor', None)
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(1.0)
    _line(c, SL_X, y, TABLE_RIGHT, y)
    # Compute the body start y (bottom of header block)
    y_body_start = y_top - HEADER_ROW_HEIGHT

    # Draw vertical lines for header and outer border in solid black
    prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
    prev_stroke = getattr(c, "_strokeColor", None)
    c.setLineWidth(0.5)
    c.setStrokeColor(RULE_COLOR)
    for x in (SL_X, DESC_X, QTY_X, RATE_X, AMT_X, TABLE_RIGHT):
        _line(c, x, y_top, x, y_body_start)
    # Restore previous stroke settings
    if prev_w is not None:
        c.setLineWidth(prev_w)
    if prev_stroke is not None:
        c.setStrokeColor(prev_stroke)

    # Restore header-level stroke settings
    if hdr_prev_w is not None:
        c.setLineWidth(hdr_prev_w)
    if hdr_prev_stroke is not None:
        c.setStrokeColor(hdr_prev_stroke)
    return y_body_start


def _ensure_table_within_page(c: Canvas, y_cursor: float, need_height: float) -> bool:
    return (y_cursor - need_height) > (MARGIN_BOTTOM + TOTALS_BLOCK_HEIGHT_MIN)


def _draw_table_rows(c: Canvas, font: str, items: List[Dict[str, Any]], start_y: float, total_items: int | None = None) -> Tuple[float, int]:
    y = start_y
    c.setFont(font, TEXT_FONT_SIZE)
    drawn = 0
    # If total_items provided, infer base index from slice length so we can compute global indices
    base_index = 0
    if total_items is not None:
        try:
            base_index = max(0, int(total_items) - len(items))
        except Exception:
            base_index = 0

    # vertical column lines (draw progressively with rows)
    # we’ll draw outer border lines as we go to keep crisp alignment
    # lighter grid lines for body
    prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
    prev_stroke = getattr(c, '_strokeColor', None)
    c.setLineWidth(0.3)
    c.setStrokeColor(GRID_COLOR)

    for idx, it in enumerate(items, start=1):
        desc = str(it.get("description", ""))
        qty = float(it.get("qty", 0) or 0)
        rate = float(it.get("rate", 0) or 0)
        amount = float(it.get("amount", qty * rate))

        wrapped = wrap_text(c, desc, DESC_W - 4, font, TEXT_FONT_SIZE)
        line_count = max(1, len(wrapped))
        row_h = line_count * ROW_HEIGHT

        # if not enough space for this row above bottom margin, stop (totals handled later)
        if y - row_h < (MARGIN_BOTTOM + ROW_BOTTOM_GAP):
            break

    # left/right verticals per row block
    # draw text
        row_top = y
        # Sl. aligned to row baseline
        c.drawString(SL_X + 2, y - row_h + 2, f"{idx}.")
        # Description multi-line
        ty = y - ROW_HEIGHT + 2
        for ln in wrapped:
            c.drawString(DESC_X + 2, ty, ln)
            ty -= ROW_HEIGHT
        # numeric right aligned at row baseline so columns align across 1–2 line rows
        baseline_y = y - row_h + 2
        c.drawRightString(QTY_X + QTY_W - 2, baseline_y, _fmt_qty(qty))
        c.drawRightString(RATE_X + RATE_W - 2, baseline_y, fmt_money(rate))
        prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
        prev_stroke = getattr(c, '_strokeColor', None)
        c.setLineWidth(0.5)
        c.setStrokeColor(RULE_COLOR)
        if total_items is not None:
            try:
                global_idx = base_index + (idx - 1)
                is_last_overall = (global_idx == total_items - 1)
            except Exception:
                is_last_overall = False
        if not is_last_overall:
            # keep a subtle horizontal separator regardless of style
            _line(c, SL_X, y - row_h, TABLE_RIGHT, y - row_h)

        # Use solid black for vertical borders and splits
        row_prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
        row_prev_stroke = getattr(c, '_strokeColor', None)
        c.setLineWidth(0.5)
        c.setStrokeColor(RULE_COLOR)

        # After drawing the text, draw vertical lines for this row block (left border, splits, right border)
        for x in (SL_X, DESC_X, QTY_X, RATE_X, AMT_X, TABLE_RIGHT):
            _line(c, x, row_top, x, y - row_h)

        # Restore stroke settings before leaving the loop iteration
        if row_prev_w is not None:
            c.setLineWidth(row_prev_w)
        if row_prev_stroke is not None:
            c.setStrokeColor(row_prev_stroke)

        y -= row_h
        drawn += 1

    # restore previous line width and color
    if prev_w is not None:
        c.setLineWidth(prev_w)
    if prev_stroke is not None:
        c.setStrokeColor(prev_stroke)
    return y, drawn


def _draw_summary(c: Canvas, font: str, bold_font: str, data: dict, y: float) -> float:
    """
    Draws a two-line summary: first line shows the thank-you message across all columns,
    second line shows the Total label/value in the Rate/Amount columns. Both lines are enclosed
    by the table’s border and column separators.
    """
    prev_w = getattr(c, "_lineWidth", None) or getattr(c, "_linewidth", None)
    prev_color = getattr(c, '_strokeColor', None)
    c.setLineWidth(0.5)
    c.setStrokeColor(RULE_COLOR)

    # First summary row – Thank you
    row_h = ROW_HEIGHT
    y_top = y
    y_bottom = y - row_h
    # Draw top separator (ties into the previous row’s bottom)
    _line(c, SL_X, y_top, TABLE_RIGHT, y_top)
    # Draw vertical lines for all columns
    for x in (SL_X, DESC_X, QTY_X, RATE_X, AMT_X, TABLE_RIGHT):
        _line(c, x, y_top, x, y_bottom)
    # Draw bottom border of this first summary row
    _line(c, SL_X, y_bottom, TABLE_RIGHT, y_bottom)
    # Write Thank you message in the Description cell
    thanks = _get(data, "settings.thank_you", "Thank you for choosing KMC!")
    c.setFont(font, TEXT_FONT_SIZE)
    c.drawString(DESC_X + 2, y_bottom + 2, thanks)

    # Second summary row – Total
    y2_top = y_bottom
    y2_bottom = y2_top - row_h
    # Top of second summary row (shared with bottom of first) is already drawn above
    # Draw vertical lines for all columns
    for x in (SL_X, DESC_X, QTY_X, RATE_X, AMT_X, TABLE_RIGHT):
        _line(c, x, y2_top, x, y2_bottom)
    # Bottom border for the final row
    _line(c, SL_X, y2_bottom, TABLE_RIGHT, y2_bottom)

    # Calculate total and draw it
    total = round(sum(float(it.get("amount", 0.0)) for it in data.get("items", [])), 2)
    c.setFont(bold_font, TEXT_FONT_SIZE + 1)
    c.drawRightString(RATE_X + RATE_W - 2, y2_bottom + 2, "Total:")
    c.drawRightString(AMT_X + AMT_W - 2, y2_bottom + 2, f"{total:.2f}")

    # Restore previous pen settings
    if prev_w is not None:
        c.setLineWidth(prev_w)
    if prev_color is not None:
        c.setStrokeColor(prev_color)

    # Return the cursor below the summary rows
    return y2_bottom


def _draw_footer(c: Canvas, font: str, data: Dict[str, Any]) -> None:
    y = MARGIN_BOTTOM + 6
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
        lines.append(f"Mobile No:{mobile}")

    if lines:
        gap = 11
        y_top = MARGIN_BOTTOM + 6 + gap * (len(lines) - 1)
        for ln in lines:
            c.drawString(x, y_top, ln)
            y_top -= gap

    # Left footer rendered as plain lines above

    # Authorized Signatory box on right
    bx = PAGE_WIDTH - MARGIN_RIGHT - SIGN_BOX_W
    by = MARGIN_BOTTOM
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
        table_start_y = min(info_y, bill_y) - TABLE_TOP_GAP
        return _draw_table_header(c, font, bold_font, table_start_y)

    y = new_page(first_page=True)

    start_index = 0
    while start_index < len(items):
        y_before = y
        y, drawn = _draw_table_rows(c, font, items[start_index:], y, total_items=len(items))
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
            # Last page: ensure there is room for totals; if not, move to fresh page
            need = TOTALS_BLOCK_HEIGHT_MIN
            if (y - need) < MARGIN_BOTTOM:
                c.showPage()
                y = new_page(first_page=False)
            # Draw totals and footer
            y = _draw_summary(c, font, bold_font, data, y)
            _draw_footer(c, font, data)

    c.save()
