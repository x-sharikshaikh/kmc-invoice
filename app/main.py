from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication, QTableWidgetItem, QMessageBox, QDialog

from app.ui_main import create_main_window
from app.core.settings import load_settings, save_settings, Settings
from app.data.db import create_db_and_tables
from app.data.repo import get_or_create_customer, create_invoice
from app.printing.print_windows import print_pdf, open_file
from app.pdf.pdf_draw import build_invoice_pdf
# Legacy PDF overlay/merge is no longer used. Kept commented for reference only.
# from app.pdf.pdf_overlay import build_overlay as build_legacy_overlay  # deprecated
# from app.pdf.pdf_merge import merge_with_template as merge_legacy      # deprecated
import logging
logger = logging.getLogger(__name__)
from app.core.numbering import bump_sequence_to_at_least, peek_next_invoice_number


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

    # Allow reloading settings from disk at runtime (e.g., after external edits)
    def _reload_settings_from_disk() -> None:
        nonlocal settings
        new_settings = load_settings()
        settings = new_settings
        # Update UI-bound settings too
        if hasattr(win, 'refresh_settings'):
            try:
                win.refresh_settings(new_settings)
            except Exception:
                pass

    # Initialize invoice number on load (peek next)
    try:
        from app.data.db import get_session
        with get_session() as s:
            win.inv_number.setText(peek_next_invoice_number(settings.invoice_prefix, s))
    except Exception:
        pass

    # Wire footer buttons
    try:
        win.btn_new_invoice.clicked.connect(win.new_invoice)
    except Exception:
        pass
    def on_save_draft():
        # Ensure settings reflect latest on-disk config
        _reload_settings_from_disk()
        issues = win.validate_form() if hasattr(win, 'validate_form') else []
        if issues:
            QMessageBox.warning(win, "Fix form errors", "\n".join(f"• {m}" for m in issues))
            return
        saved = _save_draft_to_db(win)
        # Bump sequence and refresh UI number for next invoice entry
        try:
            inv_no = saved['invoice'].number if hasattr(saved['invoice'], 'number') else win.inv_number.text().strip()
            prefix = settings.invoice_prefix
            suffix = inv_no.removeprefix(prefix)
            n = int(''.join(ch for ch in suffix if ch.isdigit())) if suffix else 0
            from app.data.db import get_session
            with get_session() as s:
                bump_sequence_to_at_least(prefix, n, s)
                # Set the next number for convenience
                win.inv_number.setText(peek_next_invoice_number(prefix, s))
        except Exception:
            pass

    def on_open_settings():
        nonlocal settings
        try:
            from app.widgets.settings_dialog import SettingsDialog
            dlg = SettingsDialog(settings, parent=win)
        except Exception:
            # If import fails for any reason, just return
            return
        if dlg.exec() == QDialog.Accepted:
            new_settings = dlg.result_settings()
            # Persist to settings.json
            save_settings(new_settings)
            # Update in-memory settings and refresh UI defaults
            settings = new_settings
            if hasattr(win, 'refresh_settings'):
                win.refresh_settings(new_settings)

    def on_save_pdf_and_optionally_print(do_print: bool = False):
        # Ensure settings reflect latest on-disk config
        _reload_settings_from_disk()
        # Ensure output directory exists before persisting anything to DB
        try:
            out_dir = _ensure_save_dir()
            if not out_dir.exists() or not out_dir.is_dir():
                raise OSError(f"Output directory is not available: {out_dir}")
        except Exception as e:
            QMessageBox.critical(
                win,
                "Cannot save PDF",
                f"Could not create or access the save folder:\n{SAVE_DIR}\n\nDetails: {e}",
            )
            return
        logger.info("Save/Print invoked (do_print=%s)", do_print)
        issues = win.validate_form() if hasattr(win, 'validate_form') else []
        if issues:
            QMessageBox.warning(win, "Fix form errors", "\n".join(f"• {m}" for m in issues))
            return
        logger.info("Validation passed")
        # Collect UI data
        collected = win.collect_data() if hasattr(win, 'collect_data') else None
        if not collected:
            # Fallback to manual collection
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
        try:
            logger.info("Collected %s items", len(collected.get('items', [])))
        except Exception:
            logger.info("Collected items")

        # Persist to DB
        try:
            saved = _save_draft_to_db(win)
            try:
                inv_no_log = saved['invoice'].number if hasattr(saved['invoice'], 'number') else collected['invoice']['number']
                logger.info("Saved invoice %s to DB", inv_no_log)
            except Exception:
                logger.info("Saved invoice to DB")
        except Exception as e:
            QMessageBox.critical(win, "Save failed", f"Could not save invoice to the database.\n\nDetails: {e}")
            return

        # Sync sequence so future peeks reflect at least this saved number
        try:
            inv_no = saved['invoice'].number if hasattr(saved['invoice'], 'number') else collected['invoice']['number']
            prefix = settings.invoice_prefix
            # Parse numeric suffix
            suffix = inv_no.removeprefix(prefix)
            n = int(''.join(ch for ch in suffix if ch.isdigit())) if suffix else 0
            from app.data.db import get_session
            with get_session() as s:
                bump_sequence_to_at_least(prefix, n, s)
        except Exception:
            pass

        # Build final PDF (code-drawn) directly
        inv_no = saved['invoice'].number if hasattr(saved['invoice'], 'number') else collected['invoice']['number']
        out_final = out_dir / f"{inv_no}.pdf"

        # Prepare data for the code-drawn generator
        pdf_data = {
            'customer': collected['customer'],
            'invoice': {
                'number': inv_no,
                'date': (getattr(saved['invoice'], 'date', None) or win.date_edit.date().toString("dd-MM-yyyy")),
                'tax_rate': settings.tax_rate,
            },
            'items': collected['items'],
            'subtotal': saved.get('subtotal'),
            'tax': saved.get('tax'),
            'total': saved.get('total'),
            'settings': {
                'business_name': settings.business_name,
                'owner': settings.owner,
                'phone': settings.phone,
                'permit': settings.permit,
                'pan': settings.pan,
                'cheque_to': settings.cheque_to,
                'thank_you': settings.thank_you,
                'invoice_prefix': settings.invoice_prefix,
                'tax_rate': settings.tax_rate,
                'logo_path': settings.logo_path,
            },
            'business': {
                'permit': settings.permit,
                'pan': settings.pan,
                'cheque_to': settings.cheque_to,
            },
        }

        # Build final PDF (always code-drawn). If legacy flag is set, warn and continue.
        try:
            if getattr(settings, 'use_template_overlay', False):
                logging.warning("use_template_overlay is deprecated and ignored; using code-drawn PDF path.")
            logger.info("Building PDF: %s", out_final)
            build_invoice_pdf(out_final, pdf_data)
            logger.info("PDF built: %s", out_final)
        except Exception as e:
            QMessageBox.critical(win, "PDF failed", f"Could not generate the PDF.\n\nDetails: {e}")
            return

        # After successful save + PDF, bump already done; set next number in UI
        try:
            from app.data.db import get_session
            with get_session() as s:
                win.inv_number.setText(peek_next_invoice_number(settings.invoice_prefix, s))
        except Exception:
            pass

        if do_print:
            try:
                ok = print_pdf(str(out_final))
                if ok is False:
                    QMessageBox.warning(win, "Print issue", "The PDF was saved, but printing may have failed. Please print it manually.")
            except Exception:
                QMessageBox.warning(win, "Print issue", "The PDF was saved, but an error occurred while printing. Please print it manually.")
        else:
            # Open the PDF in default viewer; optionally open folder on failure
            try:
                ok = open_file(str(out_final))
            except Exception:
                ok = False
            if not ok:
                # Try opening containing folder
                try:
                    from subprocess import run
                    run(["explorer", "/select,", str(out_final)])
                except Exception:
                    QMessageBox.information(win, "Saved", f"Invoice saved to:\n{out_final}")

    win.btn_save_draft.clicked.connect(on_save_draft)
    win.btn_settings.clicked.connect(on_open_settings)
    win.btn_save_pdf.clicked.connect(lambda: on_save_pdf_and_optionally_print(False))
    win.btn_print.clicked.connect(lambda: on_save_pdf_and_optionally_print(True))

    _wire_shortcuts(win)

    win.show()
    app.exec()


if __name__ == "__main__":
    main()
