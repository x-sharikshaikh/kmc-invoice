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

