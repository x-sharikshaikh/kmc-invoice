from __future__ import annotations

import sys
from pathlib import Path

# Ensure we can import the app package when running this script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date
from app.pdf.pdf_overlay import build_overlay  # type: ignore
from app.pdf.pdf_merge import merge_with_template  # type: ignore
from app.printing.print_windows import open_file  # type: ignore


def sample_data() -> dict:
    return {
        "invoice": {
            "number": "KMC-TEST-0001",
            "date": date.today().strftime("%d-%m-%Y"),
        },
        "customer": {
            "name": "Acme Corp.",
            "phone": "+91 98765 43210",
            "address": "221B Baker Street\nLondon, NW1 6XE",
        },
        "items": [
            {"description": "LED Panel Light 18W", "qty": 4, "rate": 525.00, "amount": 2100.00},
            {"description": "Concealed Wiring (per room)", "qty": 2, "rate": 1750.00, "amount": 3500.00},
            {"description": "Switchboard Replacement", "qty": 1, "rate": 950.00, "amount": 950.00},
        ],
        "total": 6550.00,
    }


def main() -> None:
    out_dir = ROOT / "tools" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    overlay_path = out_dir / "sample_overlay.pdf"
    out_pdf = ROOT / "sample_invoice.pdf"

    build_overlay(overlay_path, sample_data())
    merge_with_template(overlay_path, out_pdf)

    print(f"Sample invoice written to: {out_pdf}")
    # Auto-open for quick inspection on Windows
    open_file(str(out_pdf))


if __name__ == "__main__":
    main()
