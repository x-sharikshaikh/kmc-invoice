from __future__ import annotations

"""
Deprecated module: static template merging is no longer used.

These functions remain only for backward compatibility (tests/tools) and are
scheduled for removal once callers migrate to app.pdf.pdf_draw.build_invoice_pdf.
"""

from pathlib import Path
import warnings


def merge_overlay_with_template(template_path: Path | str, overlay_path: Path | str, out_path: Path | str) -> None:
	"""Deprecated: Template merge no longer used.

	For the code-drawn pipeline, simply copy the generated overlay to the output.
	"""
	warnings.warn(
		"merge_overlay_with_template is deprecated and will be removed; use app.pdf.pdf_draw.build_invoice_pdf",
		DeprecationWarning,
		stacklevel=2,
	)
	overlay_path = Path(overlay_path)
	out_path = Path(out_path)
	out_path.write_bytes(Path(overlay_path).read_bytes())


def merge_with_template(overlay_pdf: Path, output_pdf: Path) -> None:
	"""Code-drawn pipeline: pass-through the overlay to the final output.

	Keeping the function name preserves call sites while eliminating the template dependency.
	"""
	warnings.warn(
		"merge_with_template is deprecated and will be removed; use app.pdf.pdf_draw.build_invoice_pdf",
		DeprecationWarning,
		stacklevel=2,
	)
	overlay_pdf = Path(overlay_pdf)
	output_pdf = Path(output_pdf)
	output_pdf.write_bytes(overlay_pdf.read_bytes())

