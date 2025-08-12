from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from datetime import date
from importlib import import_module
import pkgutil

RESULTS: list[str] = []


def _ok(msg: str) -> None:
    RESULTS.append(f"OK: {msg}")


def _fail(msg: str, e: BaseException | None = None) -> None:
    if e:
        RESULTS.append(f"FAIL: {msg} -> {e}")
    else:
        RESULTS.append(f"FAIL: {msg}")


def env_info() -> None:
    _ok(f"Python {sys.version.split()[0]} on {sys.platform}")
    _ok(f"CWD: {os.getcwd()}")


def import_all_app_modules() -> None:
    try:
        import app  # ensure package available
        mods = []
        for m in pkgutil.walk_packages(app.__path__, app.__name__ + "."):
            mods.append(m.name)
        failures = 0
        for name in sorted(mods):
            try:
                import_module(name)
            except Exception as e:
                failures += 1
                _fail(f"import {name}", e)
        if failures == 0:
            _ok(f"Imported {len(mods)} modules under app/*")
        else:
            _fail(f"{failures} module(s) failed to import")
    except Exception as e:
        _fail("enumerate app modules", e)


essential_runtime_checks_ran = False

def db_and_pdf_checks(tmp_dir: Path) -> None:
    global essential_runtime_checks_ran
    try:
        from app.data.db import create_db_and_tables, get_session
        from app.data.repo import get_or_create_customer, create_invoice
        from app.pdf.pdf_draw import build_invoice_pdf
        from pypdf import PdfReader
    except Exception as e:
        _fail("import runtime modules (db/repo/pdf)", e)
        return

    try:
        create_db_and_tables()
        _ok("DB schema ensured")
    except Exception as e:
        _fail("create_db_and_tables", e)
        return

    try:
        cust = get_or_create_customer("DiagTest Customer", phone="0000000000", address="Diag Addr")
        base = f"DIAG-{date.today().strftime('%Y%m%d')}"
        inv_no = base
        inv = None
        # Try base, then append -1..-20 until it succeeds to keep the diagnostic idempotent
        for i in range(0, 21):
            try:
                candidate = inv_no if i == 0 else f"{base}-{i}"
                inv = create_invoice({
                    'number': candidate,
                    'date': date.today(),
                    'customer_id': int(cust.id),  # type: ignore[arg-type]
                    'items': [
                        {'description': 'Ping', 'qty': 1, 'rate': 1.23},
                        {'description': 'Pong', 'qty': 2, 'rate': 4.56},
                    ],
                })
                break
            except ValueError as ve:
                if "already exists" in str(ve).lower():
                    continue
                raise
        if inv is None:
            raise RuntimeError("Could not allocate a unique diagnostic invoice number")
        _ok(f"Created invoice {inv.number}")
    except Exception as e:
        _fail("create test invoice", e)
        return

    try:
        out_pdf = tmp_dir / f"{inv_no}.pdf"
        data = {
            'customer': {'name': 'Diag', 'phone': '0', 'address': 'A'},
            'invoice': {'number': inv_no, 'date': date.today()},
            'items': [
                {'description': 'Ping', 'qty': 1, 'rate': 1.23, 'amount': 1.23},
                {'description': 'Pong', 'qty': 2, 'rate': 4.56, 'amount': 9.12},
            ],
            'total': 10.35,
        }
        build_invoice_pdf(out_pdf, data)
        if out_pdf.exists() and out_pdf.stat().st_size > 0:
            _ok(f"Built PDF {out_pdf.name} ({out_pdf.stat().st_size} bytes)")
        else:
            _fail("PDF not created or empty")
            return
        # Basic text extraction
        txt = PdfReader(str(out_pdf)).pages[0].extract_text() or ""
        if "Date:" in txt and "Total:" in txt:
            _ok("PDF contains expected labels (Date/Total)")
        else:
            _fail("PDF text missing expected labels")
    except Exception as e:
        _fail("generate/read PDF", e)
        return

    essential_runtime_checks_ran = True


def main() -> None:
    tmp_dir = Path.cwd() / ".diag_out"
    tmp_dir.mkdir(exist_ok=True)

    env_info()
    import_all_app_modules()
    db_and_pdf_checks(tmp_dir)

    print("==== Diagnostics ====")
    for line in RESULTS:
        print(line)
    if essential_runtime_checks_ran:
        print("RESULT: PASS (core runtime checks succeeded)")
    else:
        print("RESULT: WARN/FAIL (see failures above)")


if __name__ == "__main__":
    main()
