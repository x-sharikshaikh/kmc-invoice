from __future__ import annotations

from pathlib import Path

import math

from pypdf import PdfReader

from app.pdf.pdf_overlay import build_overlay
from app.pdf.pdf_merge import merge_with_template


def _a4_size_points() -> tuple[float, float]:
    # ReportLab A4 in points
    return (595.2755905511812, 841.8897637795277)


def test_invoice_pdf_overlay_and_merge(tmp_path: Path) -> None:
    # Arrange: sample data with 3 items and dd-mm-yyyy date
    items = [
        {"description": "Item A", "qty": 2, "rate": 150.0, "amount": 300.0},
        {"description": "Item B", "qty": 1, "rate": 49.99, "amount": 49.99},
        {"description": "Item C", "qty": 3, "rate": 20.0, "amount": 60.0},
    ]
    expected_total = sum(i["amount"] for i in items)
    date_str = "09-08-2025"  # dd-mm-yyyy

    data = {
        "invoice": {"number": "KMC-0001", "date": date_str},
        "customer": {"name": "Test Customer", "phone": "1234567890", "address": "Line 1\nLine 2"},
        "items": items,
        "total": expected_total,
    }

    overlay_pdf = tmp_path / "overlay.pdf"
    merged_pdf = tmp_path / "merged.pdf"

    # Act: build overlay and merge with template (A4)
    build_overlay(overlay_pdf, data)
    # Merge with template if present, else function copies overlay (fallback)
    merge_with_template(overlay_pdf, merged_pdf)

    # Assert: merged has exactly one page of A4 size
    reader = PdfReader(str(merged_pdf))
    assert len(reader.pages) == 1

    page = reader.pages[0]
    box = page.mediabox
    width = float(box.right - box.left)
    height = float(box.top - box.bottom)
    a4w, a4h = _a4_size_points()
    # Allow a small tolerance for float conversions
    assert math.isclose(width, a4w, rel_tol=0, abs_tol=1.0)
    assert math.isclose(height, a4h, rel_tol=0, abs_tol=1.0)

    # Extract text and verify date and total math are present
    text = page.extract_text() or ""
    assert f"Date: {date_str}" in text
    import re
    # Allow potential newline between label and value in extracted text
    assert re.search(rf"Total:\s*{expected_total:.2f}", text) is not None

    # Sanity-check headers exist for right-aligned numeric columns
    # (alignment is enforced by drawRightString in implementation)
    assert "Qty" in text and "Rate" in text and "Amount" in text
