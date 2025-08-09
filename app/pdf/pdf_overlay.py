from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

