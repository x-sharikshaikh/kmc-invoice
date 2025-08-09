from __future__ import annotations

from pathlib import Path
from app.pdf.pdf_overlay import build_overlay
from app.pdf.pdf_merge import merge_overlay_with_template
from app.core.paths import resource_path

# Generates a redacted sample invoice PDF for README/demo purposes.

def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "assets" / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay = out_dir / "sample-overlay.pdf"
    out_pdf = out_dir / "sample-redacted.pdf"

    # Use provided template in assets; falls back if missing
    template = resource_path("assets/template.pdf")

    sample = {
        "business": {
            "name": "KMC Electrical",
            "owner": "(redacted)",
            "phone": "(redacted)",
            "permit": "(redacted)",
            "pan": "(redacted)",
        },
        "invoice": {"number": "KM-00001", "date": "09-08-2025"},
        "customer": {
            "name": "(Customer Name)",
            "phone": "(redacted)",
            "address": "(Street)\n(City)",
        },
        "items": [
            {"description": "Sample item A", "qty": 1, "rate": 100.0, "amount": 100.0},
            {"description": "Sample item B", "qty": 2, "rate": 150.0, "amount": 300.0},
            {"description": "Sample item C", "qty": 3, "rate": 200.0, "amount": 600.0},
        ],
        "subtotal": 1000.0,
        "tax": 0.0,
        "total": 1000.0,
        "settings": {"logo": str(resource_path("assets/logo.png"))},
    }

    build_overlay(overlay, sample)
    if template.exists():
        merge_overlay_with_template(template, overlay, out_pdf)
    else:
        # If template missing, just copy overlay
        out_pdf.write_bytes(overlay.read_bytes())

    print(f"Wrote sample to: {out_pdf}")


if __name__ == "__main__":
    main()
