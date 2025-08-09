from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.ui_main import create_main_window
from app.core.settings import load_settings
from app.data.db import create_db_and_tables
from app.data.repo import get_or_create_customer, create_invoice
from app.printing.print_windows import print_pdf
from app.pdf.pdf_overlay import build_invoice_pdf
from app.pdf.pdf_merge import merge_overlay_with_template


SAVE_DIR = Path.home() / "Documents" / "KMC Invoices"


def _collect_items_from_table(win) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    rows = win.table.rowCount()
    for r in range(rows):
        desc_it = win.table.item(r, 1)
        qty_it = win.table.item(r, 2)
        rate_it = win.table.item(r, 3)
        amt_it = win.table.item(r, 4)
        def _f(it: QTableWidgetItem | None) -> float:
            try:
                return float(it.text()) if it and it.text() else 0.0
            except Exception:
                return 0.0
        items.append({
            "description": (desc_it.text() if desc_it else "").strip(),
            "qty": _f(qty_it),
            "rate": _f(rate_it),
            "amount": _f(amt_it),
        })
    return items


def _save_draft_to_db(win) -> Dict[str, Any]:
    """Persist the current form to DB and return a dict with saved invoice data."""
    settings = win.settings
    # Customer
    name = win.name_edit.text().strip()
    phone = win.phone_edit.text().strip()
    addr = win.addr_edit.toPlainText().strip()
    cust = get_or_create_customer(name, phone, addr)

    # Invoice DTO
    qd = win.date_edit.date()
    from datetime import date as _date
    inv_date = _date(qd.year(), qd.month(), qd.day())
    items = _collect_items_from_table(win)
    subtotal = sum(i["amount"] for i in items)
    tax = subtotal * float(settings.tax_rate)
    total = subtotal + tax
    dto = {
        "number": win.inv_number.text().strip(),
        "date": inv_date,
        "customer_id": cust.id,
        "notes": None,
        "tax": tax,
        "items": items,
    }
    inv = create_invoice(dto)
    return {
        "invoice": inv,
        "customer": cust,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
    }


def _ensure_save_dir() -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return SAVE_DIR


def _wire_shortcuts(win) -> None:
    # Enter/Return -> Add Row (when table or its editor has focus)
    def _add_if_table():
        fw = win.focusWidget()
        # Apply when table or editing a cell
        if fw is win.table or (fw and fw.parent() is win.table):
            win.add_row()
    for key in (Qt.Key_Return, Qt.Key_Enter):
        sc = QShortcut(key, win)
        sc.activated.connect(_add_if_table)

    # Delete -> Remove selected rows
    del_sc = QShortcut(Qt.Key_Delete, win)
    del_sc.activated.connect(win.remove_selected_rows)

    # Tab order (basic through bill-to and into table)
    win.setTabOrder(win.name_edit, win.phone_edit)
    win.setTabOrder(win.phone_edit, win.addr_edit)
    win.setTabOrder(win.addr_edit, win.table)


def main() -> None:
    app = QApplication()
    settings = load_settings()
    create_db_and_tables()

    win = create_main_window()

    # Wire footer buttons
    def on_save_draft():
        _save_draft_to_db(win)

    def on_save_pdf_and_optionally_print(do_print: bool = False):
        saved = _save_draft_to_db(win)
        data = {
            "business": {
                "name": settings.business_name,
                "owner": settings.owner,
                "phone": settings.phone,
                "permit": settings.permit,
                "pan": settings.pan,
                "cheque_to": settings.cheque_to,
                "thank_you": settings.thank_you,
            },
            "invoice": {
                "number": win.inv_number.text().strip(),
                "date": win.date_edit.date().toString("dd-MM-yyyy"),
            },
            "customer": {
                "name": win.name_edit.text().strip(),
                "phone": win.phone_edit.text().strip(),
                "address": win.addr_edit.toPlainText().strip(),
            },
            "items": _collect_items_from_table(win),
            "subtotal": saved["subtotal"],
            "tax": saved["tax"],
            "total": saved["total"],
            "settings": {
                "logo": str((Path(__file__).resolve().parents[2] / "assets" / "logo.png").as_posix()),
                "template": str((Path(__file__).resolve().parents[2] / "assets" / "template.pdf").as_posix()),
                "font": str((Path(__file__).resolve().parents[2] / settings.pdf.get("fontRegular", "assets/fonts/NotoSans-Regular.ttf")).as_posix()) if isinstance(getattr(settings, 'pdf', {}), dict) else str((Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NotoSans-Regular.ttf").as_posix()),
            },
        }

        out_dir = _ensure_save_dir()
        out_overlay = out_dir / f"{data['invoice']['number']}_overlay.pdf"
        out_final = out_dir / f"{data['invoice']['number']}.pdf"

        build_invoice_pdf(data, out_overlay)
        template = Path(data["settings"]["template"]) if data["settings"]["template"] else None
        if template and template.exists():
            merge_overlay_with_template(template, out_overlay, out_final)
            out_overlay.unlink(missing_ok=True)
        else:
            # No template; use overlay as final
            out_final.write_bytes(out_overlay.read_bytes())
            out_overlay.unlink(missing_ok=True)

        if do_print:
            print_pdf(str(out_final))

    win.btn_save_draft.clicked.connect(on_save_draft)
    win.btn_save_pdf.clicked.connect(lambda: on_save_pdf_and_optionally_print(False))
    win.btn_print.clicked.connect(lambda: on_save_pdf_and_optionally_print(True))

    _wire_shortcuts(win)

    win.show()
    app.exec()


if __name__ == "__main__":
    main()
