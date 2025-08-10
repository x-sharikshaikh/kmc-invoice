from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from app.pdf.pdf_draw import build_invoice_pdf
from app.core.settings import load_settings


def _items() -> list[dict]:
    # 5 realistic items within 3–8 items range
    rows = [
        {"description": "Electrical inspection and diagnostics", "qty": 1, "rate": 120.00},
        {"description": "Wiring repair (per room)", "qty": 2, "rate": 85.50},
        {"description": "LED fixture installation", "qty": 3, "rate": 45.00},
        {"description": "Breaker replacement", "qty": 1, "rate": 65.75},
        {"description": "Safety compliance testing", "qty": 1, "rate": 90.00},
    ]
    for r in rows:
        r["amount"] = round(float(r["qty"]) * float(r["rate"]), 2)
    return rows


def main() -> None:
    settings = load_settings()

    items = _items()
    subtotal = round(sum(r["amount"] for r in items), 2)
    total = round(subtotal, 2)

    data = {
        "customer": {"name": "Sample Customer", "phone": "(555) 012-3456", "address": "123 Sample St\nMetropolis"},
    "invoice": {"number": "SAMPLE", "date": _date.today()},
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
        },
        "business": {"permit": settings.permit, "pan": settings.pan, "cheque_to": settings.cheque_to},
    }

    out_dir = Path.home() / "Documents" / "KMC Invoices"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / "SAMPLE_CODE_DRAWN.pdf"

    build_invoice_pdf(out_pdf, data)
    print(f"Wrote sample to: {out_pdf}")


if __name__ == "__main__":
    main()
