from __future__ import annotations

from datetime import date as _date
from pathlib import Path
import sys

# Ensure we can import the app package when running this script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.settings import load_settings
from app.pdf.pdf_draw import build_invoice_pdf
from app.printing.print_windows import open_file


def sample_data() -> dict:
    items = [
        {"description": "LED Panel Light 18W", "qty": 4, "rate": 525.00},
        {"description": "Concealed Wiring (per room)", "qty": 2, "rate": 1750.00},
        {"description": "Switchboard Replacement", "qty": 1, "rate": 950.00},
    ]
    for it in items:
        it["amount"] = round(float(it["qty"]) * float(it["rate"]), 2)
    subtotal = round(sum(i["amount"] for i in items), 2)
    settings = load_settings()
    total = round(subtotal, 2)

    return {
    "invoice": {"number": "KMC-TEST-0001", "date": _date.today()},
        "customer": {"name": "Acme Corp.", "phone": "+91 98765 43210", "address": "221B Baker Street\nLondon, NW1 6XE"},
        "items": items,
        "subtotal": subtotal,
    # legacy key kept for compatibility; unused
    "tax": 0.0,
        "total": total,
        "settings": {
            "business_name": settings.business_name,
            "owner": settings.owner,
            "phone": settings.phone,
            "permit": settings.permit,
            "pan": settings.pan,
            "cheque_to": settings.cheque_to,
            "thank_you": settings.thank_you,
            "invoice_prefix": settings.invoice_prefix,
            # no tax in new flow
            "tax_rate": 0.0,
            "logo_path": settings.logo_path,
            "name_logo_path": getattr(settings, "name_logo_path", None),
            "signature_path": getattr(settings, "signature_path", None),
        },
        "business": {"permit": settings.permit, "pan": settings.pan, "cheque_to": settings.cheque_to},
    }


def main() -> None:
    # Write under Documents/KMC Invoices for consistency
    out_dir = Path.home() / "Documents" / "KMC Invoices"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / "sample_invoice.pdf"

    build_invoice_pdf(out_pdf, sample_data())
    print(f"Sample invoice written to: {out_pdf}")
    # Auto-open for quick inspection on Windows
    open_file(str(out_pdf))


if __name__ == "__main__":
    main()
