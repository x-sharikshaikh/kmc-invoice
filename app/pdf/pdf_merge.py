from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def merge_overlay_with_template(template_path: Path | str, overlay_path: Path | str, out_path: Path | str) -> None:
	template_path = Path(template_path)
	overlay_path = Path(overlay_path)
	out_path = Path(out_path)

	tpl_reader = PdfReader(str(template_path))
	ovl_reader = PdfReader(str(overlay_path))

	writer = PdfWriter()

	# Merge first page overlay with first page of template, then append remaining overlay pages (if any)
	base_page = tpl_reader.pages[0]
	overlay_page = ovl_reader.pages[0]
	base_page.merge_page(overlay_page)
	writer.add_page(base_page)

	for i in range(1, len(ovl_reader.pages)):
		writer.add_page(ovl_reader.pages[i])

	with out_path.open("wb") as f:
		writer.write(f)


def merge_with_template(overlay_pdf: Path, output_pdf: Path) -> None:
	"""Overlay the given transparent overlay PDF onto assets/template.pdf.

	The output page size matches the template's mediabox to keep the background crisp.
	If the template is missing, the overlay is copied to output as a fallback.
	"""
	root = Path(__file__).resolve().parents[2]
	template_path = root / "assets" / "template.pdf"

	overlay_pdf = Path(overlay_pdf)
	output_pdf = Path(output_pdf)

	if not template_path.exists():
		# Fallback: no template available, just pass through the overlay
		output_pdf.write_bytes(overlay_pdf.read_bytes())
		return

	tpl_reader = PdfReader(str(template_path))
	ovl_reader = PdfReader(str(overlay_pdf))

	writer = PdfWriter()

	# Use the template's first page as the base and merge the overlay's first page on top
	base_page = tpl_reader.pages[0]
	overlay_page = ovl_reader.pages[0]

	# Merge without rasterizing to keep background crisp
	base_page.merge_page(overlay_page)
	writer.add_page(base_page)

	# Append any additional overlay pages unchanged
	for i in range(1, len(ovl_reader.pages)):
		writer.add_page(ovl_reader.pages[i])

	with output_pdf.open("wb") as f:
		writer.write(f)

