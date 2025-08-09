from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict, Tuple, Iterable

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.core.paths import resource_path

try:
	from pypdf import PdfReader  # to read template size if available
except Exception:  # optional
	PdfReader = None  # type: ignore


def _page_size_from_template(template_path: Path | None) -> Tuple[float, float]:
	if template_path and PdfReader is not None and template_path.exists():
		try:
			r = PdfReader(str(template_path))
			page = r.pages[0]
			box = page.mediabox
			width = float(box.right - box.left)
			height = float(box.top - box.bottom)
			return width, height
		except Exception:
			pass
	return A4  # fallback


def _register_font(ttf_path: Path | None) -> str:
	# Returns the font name to use
	if ttf_path and ttf_path.exists():
		try:
			pdfmetrics.registerFont(TTFont("NotoSans", str(ttf_path)))
			return "NotoSans"
		except Exception:
			pass
	return "Helvetica"


def build_invoice_pdf(data: Dict[str, Any], out_path: Path | str) -> None:
	"""Create a simple overlay PDF for the invoice using reportlab.

	data expects keys: business, invoice, customer, items, subtotal, tax, total, settings{logo, template, font}
	"""
	out_path = Path(out_path)
	settings = data.get("settings", {})
	template_path = Path(settings.get("template")) if settings.get("template") else None
	font_path = Path(settings.get("font")) if settings.get("font") else None
	logo_path = Path(settings.get("logo")) if settings.get("logo") else None

	page_size = _page_size_from_template(template_path)
	font_name = _register_font(font_path)

	c = canvas.Canvas(str(out_path), pagesize=page_size)
	c.setAuthor(data.get("business", {}).get("name", ""))
	c.setTitle(f"Invoice {data.get('invoice', {}).get('number', '')}")

	# Margins
	left = 20 * mm
	top_y = page_size[1] - 20 * mm

	# Logo
	if logo_path and logo_path.exists():
		try:
			c.drawImage(str(logo_path), left, top_y - 20 * mm, width=30 * mm, height=20 * mm, preserveAspectRatio=True, mask='auto')
		except Exception:
			pass

	# Header text
	c.setFont(font_name, 16)
	c.drawString(left + 35 * mm, top_y - 5 * mm, data.get("business", {}).get("name", "KMC Electrical"))
	c.setFont(font_name, 10)
	biz = data.get("business", {})
	c.drawString(left + 35 * mm, top_y - 11 * mm, f"Owner: {biz.get('owner','')}")
	c.drawString(left + 35 * mm, top_y - 16 * mm, f"Phone: {biz.get('phone','')}")
	c.drawString(left + 35 * mm, top_y - 21 * mm, f"Permit: {biz.get('permit','')}")
	c.drawString(left + 35 * mm, top_y - 26 * mm, f"PAN: {biz.get('pan','')}")

	# Bill To & Invoice Info
	c.setFont(font_name, 11)
	c.drawString(left, top_y - 35 * mm, "BILL TO")
	cust = data.get("customer", {})
	c.setFont(font_name, 10)
	c.drawString(left, top_y - 41 * mm, cust.get("name", ""))
	c.drawString(left, top_y - 46 * mm, cust.get("phone", ""))
	c.drawString(left, top_y - 51 * mm, cust.get("address", ""))

	inv = data.get("invoice", {})
	c.setFont(font_name, 11)
	c.drawString(left + 100 * mm, top_y - 35 * mm, "Invoice Info")
	c.setFont(font_name, 10)
	c.drawString(left + 100 * mm, top_y - 41 * mm, f"Number: {inv.get('number','')}")
	c.drawString(left + 100 * mm, top_y - 46 * mm, f"Date: {inv.get('date','')}")

	# Table headers
	y = top_y - 62 * mm
	c.setFont(font_name, 10)
	c.drawString(left, y, "Sl.")
	c.drawString(left + 15 * mm, y, "Description")
	c.drawRightString(left + 115 * mm, y, "Qty")
	c.drawRightString(left + 145 * mm, y, "Rate")
	c.drawRightString(left + 180 * mm, y, "Amount")
	y -= 6
	c.line(left, y, left + 180 * mm, y)
	y -= 6

	# Rows
	items = data.get("items", [])
	for i, it in enumerate(items, start=1):
		if y < 30 * mm:
			# New page if too low
			c.showPage()
			y = page_size[1] - 40 * mm
			c.setFont(font_name, 10)
		c.drawString(left, y, str(i))
		c.drawString(left + 15 * mm, y, str(it.get("description", ""))[:60])
		c.drawRightString(left + 115 * mm, y, f"{float(it.get('qty',0)):g}")
		c.drawRightString(left + 145 * mm, y, f"{float(it.get('rate',0)):.2f}")
		c.drawRightString(left + 180 * mm, y, f"{float(it.get('amount',0)):.2f}")
		y -= 6 * mm / 1.5

	# Totals
	y -= 6
	c.line(left, y, left + 180 * mm, y)
	y -= 10
	c.setFont(font_name, 11)
	c.drawRightString(left + 160 * mm, y, "Subtotal:")
	c.drawRightString(left + 180 * mm, y, f"{float(data.get('subtotal',0)):.2f}")
	y -= 6
	c.setFont(font_name, 10)
	c.drawRightString(left + 160 * mm, y, "Tax:")
	c.drawRightString(left + 180 * mm, y, f"{float(data.get('tax',0)):.2f}")
	y -= 8
	c.setFont(font_name, 12)
	c.drawRightString(left + 160 * mm, y, "Total:")
	c.drawRightString(left + 180 * mm, y, f"{float(data.get('total',0)):.2f}")

	# Footer
	y -= 12
	thanks = biz.get("thank_you", "Thank you for your business!")
	c.setFont(font_name, 10)
	c.drawString(left, y, thanks)

	c.showPage()
	c.save()


# === New explicit overlay function with A4 and tweakable coordinates ===

# Coordinates and sizes (in points) for fast tweaking
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
MARGIN_LEFT = 15 * mm
MARGIN_TOP = 15 * mm
TOP_Y = PAGE_HEIGHT - MARGIN_TOP

# Top-right invoice info block
INV_BLOCK_X = PAGE_WIDTH - 80 * mm
INV_NO_Y = TOP_Y - 5 * mm
INV_DATE_Y = INV_NO_Y - 6 * mm

# Bill To block (left)
BILL_X = MARGIN_LEFT
BILL_TITLE_Y = TOP_Y - 25 * mm
BILL_NAME_Y = BILL_TITLE_Y - 6 * mm
BILL_PHONE_Y = BILL_NAME_Y - 5 * mm
BILL_ADDR_Y = BILL_PHONE_Y - 5 * mm
BILL_ADDR_LINE_SPACING = 4.5 * mm

# Table positions
TABLE_TOP_Y = BILL_ADDR_Y - 20 * mm
SL_X = MARGIN_LEFT
DESC_X = SL_X + 15 * mm
# Note: numeric columns are anchored off of AMT_X to keep a consistent vertical grid
AMT_X = DESC_X + 160 * mm  # anchor for right-aligned numeric columns
RATE_TO_AMT_GAP = 35 * mm
QTY_TO_RATE_GAP = 30 * mm
RATE_X = AMT_X - RATE_TO_AMT_GAP
QTY_X = RATE_X - QTY_TO_RATE_GAP
TABLE_WIDTH = AMT_X - SL_X
ROW_HEIGHT = 6 * mm

# Totals row
TOTAL_Y_OFFSET = 10 * mm  # space above totals from last row

# Optional offsets (runtime-tweakable via JSON file)
ROOT = Path(__file__).resolve().parents[2]
OFFSETS_PATH = ROOT / "assets" / "overlay_offsets.json"


def _load_overlay_offsets() -> dict:
	try:
		if OFFSETS_PATH.exists():
			data = json.loads(OFFSETS_PATH.read_text(encoding="utf-8"))
			if isinstance(data, dict):
				return data
	except Exception:
		pass
	return {}


_OFF = _load_overlay_offsets()

# Block-level shifts
BILL_DX = float(_OFF.get("bill_dx", 0))
BILL_DY = float(_OFF.get("bill_dy", 0))

INV_DX = float(_OFF.get("inv_dx", 0))
INV_DY = float(_OFF.get("inv_dy", 0))
INV_NO_DX = float(_OFF.get("inv_no_dx", INV_DX))
INV_NO_DY = float(_OFF.get("inv_no_dy", INV_DY))
INV_DATE_DX = float(_OFF.get("inv_date_dx", INV_DX))
INV_DATE_DY = float(_OFF.get("inv_date_dy", INV_DY))

TABLE_DX = float(_OFF.get("table_dx", 0))
TABLE_DY = float(_OFF.get("table_dy", 0))

# Column nudges within the table
COL_QTY_DX = float(_OFF.get("col_qty_dx", 0))
COL_RATE_DX = float(_OFF.get("col_rate_dx", 0))
COL_AMT_DX = float(_OFF.get("col_amt_dx", 0))

# Totals extra nudge
TOTAL_DX = float(_OFF.get("total_dx", 0))
TOTAL_DY = float(_OFF.get("total_dy", 0))

# Baseline nudge for first row (points). Positive moves text down.
FIRST_ROW_DY = float(_OFF.get("first_row_dy", 0))


def _val(data: Dict[str, Any], *keys: str, default: str = "") -> str:
	for k in keys:
		if "." in k:
			cur: Any = data
			ok = True
			for part in k.split("."):
				if isinstance(cur, dict) and part in cur:
					cur = cur[part]
				else:
					ok = False
					break
			if ok and cur is not None:
				return str(cur)
		else:
			if k in data and data[k] is not None:
				return str(data[k])
	return default


def _split_lines(text: str) -> Iterable[str]:
	return (ln for ln in (text or "").splitlines() if ln is not None)


def build_overlay(tmp_path: Path, data: Dict[str, Any]) -> None:
	"""Write a simple A4 overlay PDF for invoice data.

	Expects data keys (direct or nested):
	  - invoice_no or invoice.number
	  - date or invoice.date (string already formatted)
	  - customer_name or customer.name
	  - phone or customer.phone
	  - address or customer.address (may contain newlines)
	  - items: list of {description, qty, rate, amount}
	  - total (optional; if missing, computed from items)
	"""
	# Resolve font path
	font_path = resource_path("assets/fonts/NotoSans-Regular.ttf")
	font_name = _register_font(font_path if font_path.exists() else None)

	tmp_path.parent.mkdir(parents=True, exist_ok=True)
	c = canvas.Canvas(str(tmp_path), pagesize=PAGE_SIZE)
	c.setFont(font_name, 10)

	# Invoice info (top-right)
	inv_no = _val(data, "invoice_no", "invoice.number")
	inv_date = _val(data, "date", "invoice.date")
	c.drawRightString(PAGE_WIDTH - MARGIN_LEFT + INV_NO_DX, INV_NO_Y + INV_NO_DY, f"Invoice: {inv_no}")
	c.drawRightString(PAGE_WIDTH - MARGIN_LEFT + INV_DATE_DX, INV_DATE_Y + INV_DATE_DY, f"Date: {inv_date}")

	# Bill To (left)
	c.setFont(font_name, 11)
	c.drawString(BILL_X + BILL_DX, BILL_TITLE_Y + BILL_DY, "BILL TO")
	c.setFont(font_name, 10)
	cust_name = _val(data, "customer_name", "customer.name")
	cust_phone = _val(data, "phone", "customer.phone")
	cust_addr = _val(data, "address", "customer.address")
	c.drawString(BILL_X + BILL_DX, BILL_NAME_Y + BILL_DY, cust_name)
	c.drawString(BILL_X + BILL_DX, BILL_PHONE_Y + BILL_DY, cust_phone)
	y_addr = BILL_ADDR_Y + BILL_DY
	for ln in _split_lines(cust_addr):
		c.drawString(BILL_X + BILL_DX, y_addr, ln)
		y_addr -= BILL_ADDR_LINE_SPACING

	# Table headers
	# Apply table-level shifts and per-column nudges.
	# Keep numeric columns right-aligned to the Amount column's vertical grid by deriving positions from AMT_X.
	y = TABLE_TOP_Y + TABLE_DY
	SL_X2 = SL_X + TABLE_DX
	DESC_X2 = DESC_X + TABLE_DX
	AMT_X2 = AMT_X + TABLE_DX + COL_AMT_DX
	RATE_X2 = AMT_X2 - RATE_TO_AMT_GAP + COL_RATE_DX
	QTY_X2 = RATE_X2 - QTY_TO_RATE_GAP + COL_QTY_DX
	c.setFont(font_name, 10)
	c.drawString(SL_X2, y, "Sl.")
	c.drawString(DESC_X2, y, "Description")
	c.drawRightString(QTY_X2, y, "Qty")
	c.drawRightString(RATE_X2, y, "Rate")
	c.drawRightString(AMT_X2, y, "Amount")
	y -= 4
	c.line(SL_X2, y, SL_X2 + TABLE_WIDTH, y)
	y -= ROW_HEIGHT / 2
	# First row baseline fine-tune (in points)
	y += FIRST_ROW_DY

	# Rows
	items = data.get("items", []) or []
	for i, it in enumerate(items, start=1):
		# Stop if near bottom; in this simple overlay, we don't paginate
		if y < 40 * mm:
			break
		desc = str(it.get("description", ""))
		qty = float(it.get("qty", 0) or 0)
		rate = float(it.get("rate", 0) or 0)
		amount = float(it.get("amount", qty * rate))
		c.setFont(font_name, 10)
		c.drawString(SL_X2, y, str(i))
		c.drawString(DESC_X2, y, desc[:80])
		c.drawRightString(QTY_X2, y, f"{qty:g}")
		c.drawRightString(RATE_X2, y, f"{rate:.2f}")
		c.drawRightString(AMT_X2, y, f"{amount:.2f}")
		y -= ROW_HEIGHT

	# Totals line and value
	y -= (TOTAL_Y_OFFSET + TOTAL_DY)
	c.line(SL_X2, y, SL_X2 + TABLE_WIDTH, y)
	y -= ROW_HEIGHT
	total = data.get("total")
	if total is None:
		total = 0.0
		for it in items:
			q = float(it.get("qty", 0) or 0)
			r = float(it.get("rate", 0) or 0)
			total += q * r
	c.setFont(font_name, 11)
	c.drawRightString(RATE_X2 + TOTAL_DX, y, "Total:")
	c.drawRightString(AMT_X2 + TOTAL_DX, y, f"{float(total):.2f}")

	c.showPage()
	c.save()

