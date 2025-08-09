from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication, QTableWidgetItem, QMessageBox

from app.ui_main import create_main_window
from app.core.settings import load_settings
from app.data.db import create_db_and_tables
from app.data.repo import get_or_create_customer, create_invoice
from app.printing.print_windows import print_pdf, open_file
from app.pdf.pdf_overlay import build_overlay
from app.pdf.pdf_merge import merge_with_template


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
        issues = win.validate_form() if hasattr(win, 'validate_form') else []
        if issues:
            QMessageBox.warning(win, "Fix form errors", "\n".join(f"• {m}" for m in issues))
            return
        _save_draft_to_db(win)

    def on_save_pdf_and_optionally_print(do_print: bool = False):
        issues = win.validate_form() if hasattr(win, 'validate_form') else []
        if issues:
            QMessageBox.warning(win, "Fix form errors", "\n".join(f"• {m}" for m in issues))
            return
        # Collect UI data
        collected = win.collect_data() if hasattr(win, 'collect_data') else None
        if not collected:
            # Fallback to legacy path
            collected = {
                'customer': {
                    'name': win.name_edit.text().strip(),
                    'phone': win.phone_edit.text().strip(),
                    'address': win.addr_edit.toPlainText().strip(),
                },
                'invoice': {
                    'number': win.inv_number.text().strip(),
                    'date': win.date_edit.date().toString("dd-MM-yyyy"),
                },
                'items': _collect_items_from_table(win),
            }

        # Persist to DB
        saved = _save_draft_to_db(win)

        # Build overlay with minimal data shape expected by build_overlay
        overlay_data = {
            'invoice': {
                'number': saved['invoice'].number if hasattr(saved['invoice'], 'number') else collected['invoice']['number'],
                'date': win.date_edit.date().toString("dd-MM-yyyy"),
            },
            'customer': collected['customer'],
            'items': collected['items'],
            'total': collected.get('total'),
        }

        out_dir = _ensure_save_dir()
        inv_no = overlay_data['invoice']['number']
        out_overlay = out_dir / f"{inv_no}_overlay.pdf"
        out_final = out_dir / f"{inv_no}.pdf"

        build_overlay(out_overlay, overlay_data)
        # Always try to merge with the bundled template; function will fallback if missing
        merge_with_template(out_overlay, out_final)
        out_overlay.unlink(missing_ok=True)

        if do_print:
            print_pdf(str(out_final))
        else:
            # Open the PDF in default viewer; optionally open folder on failure
            ok = open_file(str(out_final))
            if not ok:
                # Try opening containing folder
                try:
                    from subprocess import run
                    run(["explorer", "/select,", str(out_final)])
                except Exception:
                    pass

    win.btn_save_draft.clicked.connect(on_save_draft)
    win.btn_save_pdf.clicked.connect(lambda: on_save_pdf_and_optionally_print(False))
    win.btn_print.clicked.connect(lambda: on_save_pdf_and_optionally_print(True))

    _wire_shortcuts(win)

    win.show()
    app.exec()


if __name__ == "__main__":
    main()
