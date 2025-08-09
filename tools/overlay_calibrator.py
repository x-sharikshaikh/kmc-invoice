from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Ensure we can import the app package when running this script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pdf.pdf_overlay import (  # type: ignore
    PAGE_WIDTH,
    PAGE_HEIGHT,
    MARGIN_LEFT,
    INV_NO_Y,
    INV_DATE_Y,
    BILL_X,
    BILL_TITLE_Y,
    TABLE_TOP_Y,
    ROW_HEIGHT,
    SL_X,
    DESC_X,
    QTY_X,
    RATE_X,
    AMT_X,
)
from app.pdf.pdf_merge import merge_with_template  # type: ignore


def _draw_grid(c: canvas.Canvas, step: int = 20) -> None:
    """Draw a faint grid and coordinate ticks on the whole page.

    - Light grid every `step` points
    - Darker grid every 100 points
    - Numeric tick labels every 100 points at top/left
    """
    width, height = PAGE_WIDTH, PAGE_HEIGHT

    # Light grid
    c.setLineWidth(0.2)
    c.setStrokeGray(0.85)
    for x in range(0, int(width) + 1, step):
        c.line(x, 0, x, height)
    for y in range(0, int(height) + 1, step):
        c.line(0, y, width, y)

    # Darker 100-pt lines
    c.setLineWidth(0.4)
    c.setStrokeGray(0.65)
    for x in range(0, int(width) + 1, 100):
        c.line(x, 0, x, height)
    for y in range(0, int(height) + 1, 100):
        c.line(0, y, width, y)

    # Tick labels
    c.setFillGray(0.35)
    c.setFont("Helvetica", 7)
    for x in range(0, int(width) + 1, 100):
        c.drawString(x + 2, height - 10, str(x))
    for y in range(0, int(height) + 1, 100):
        c.drawString(2, y + 2, str(y))


def _crosshair(c: canvas.Canvas, x: float, y: float, label: str, color: Tuple[float, float, float] = (0.8, 0.1, 0.1)) -> None:
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(0.7)
    size = 6
    c.line(x - size, y, x + size, y)
    c.line(x, y - size, x, y + size)
    c.setFont("Helvetica", 8)
    c.drawString(x + 4, y + 4, label)


def build_calibration_overlay(out_overlay: Path, grid_step: int = 20) -> None:
    """Create a calibration overlay PDF with a grid and key-position markers."""
    out_overlay.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_overlay), pagesize=A4)

    # Page-wide grid
    _draw_grid(c, grid_step)

    # Key block markers using the current overlay constants
    _crosshair(c, BILL_X, BILL_TITLE_Y, "BILL TO title")
    _crosshair(c, PAGE_WIDTH - MARGIN_LEFT, INV_NO_Y, "Invoice No (right aligned)")
    _crosshair(c, PAGE_WIDTH - MARGIN_LEFT, INV_DATE_Y, "Invoice Date (right aligned)")

    # First item row origin approximation: after header line and half-row spacing
    first_row_y = TABLE_TOP_Y - 4 - (ROW_HEIGHT / 2)
    _crosshair(c, SL_X, first_row_y, "Items row Y @ Sl.")
    _crosshair(c, DESC_X, first_row_y, "Description X")
    _crosshair(c, QTY_X, first_row_y, "Qty X (right)")
    _crosshair(c, RATE_X, first_row_y, "Rate X (right)")
    _crosshair(c, AMT_X, first_row_y, "Amount X (right)")

    c.showPage()
    c.save()


def main() -> None:
    out_dir = ROOT / "tools" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    overlay_path = out_dir / "calibrate_overlay.pdf"
    out_pdf = ROOT / "calibrate.pdf"

    build_calibration_overlay(overlay_path, grid_step=20)

    # Merge with template (falls back to pass-through if missing)
    merge_with_template(overlay_path, out_pdf)

    print(f"Calibration PDF written to: {out_pdf}")


if __name__ == "__main__":
    main()
