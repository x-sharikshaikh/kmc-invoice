from __future__ import annotations

# Allow running this file directly (python app/main.py) by ensuring the project root is on sys.path
import os
import sys
if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog

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


def _collect_items(win) -> List[Dict[str, Any]]:
    """Collect line items from the LineItemsWidget only (legacy table removed)."""
    try:
        if hasattr(win, "items") and hasattr(win.items, "get_items"):
            return list(win.items.get_items())  # type: ignore[no-any-return]
    except Exception:
        pass
    # Fallback to empty list if widget is missing or errored
    return []


def _save_draft_to_db(win) -> Dict[str, Any]:
    """Persist the current invoice to the DB and return a dict with persisted objects and totals.

    Returns keys:
    - invoice: persisted Invoice instance
    - customer: persisted Customer instance
    - items: list of item dicts used for persistence
    - total: numeric grand total (sum of item amounts)
    """
    # Customer
    name = win.name_edit.text().strip()
    phone = win.phone_edit.text().strip()
    addr = win.addr_edit.toPlainText().strip()
    cust = get_or_create_customer(name, phone, addr)

    # Invoice DTO
    qd = win.date_edit.date()
    from datetime import date as _date
    inv_date = _date(qd.year(), qd.month(), qd.day())
    items = _collect_items(win)
    total = sum(i.get("amount", 0) for i in items)
    dto = {
        "number": win.inv_number.text().strip(),
        "date": inv_date,
        "customer_id": cust.id,
        "notes": None,
        "items": items,
    }
    inv = create_invoice(dto)
    return {
        "invoice": inv,
        "customer": cust,
        "items": items,
        "total": total,
    }


def _ensure_save_dir() -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return SAVE_DIR


def _wire_shortcuts(win) -> None:
    # Enter/Return -> Add Row (when focus is within the items widget)
    def _is_within_items_widget() -> bool:
        try:
            fw = win.focusWidget()
            w = fw
            while w is not None:
                if w is getattr(win, "items", None):
                    return True
                w = w.parentWidget() if hasattr(w, "parentWidget") else None
        except Exception:
            return False
        return False

    def _add_if_in_items():
        if _is_within_items_widget() and hasattr(win, "items"):
            try:
                win.items.add_row()
            except Exception:
                pass

    for key in (Qt.Key_Return, Qt.Key_Enter):
        sc = QShortcut(key, win)
        sc.activated.connect(_add_if_in_items)

    # Delete -> remove the currently focused row (if focus is inside a LineItemRow)
    def _delete_current_row():
        try:
            from app.widgets.line_items_widget import LineItemRow  # local import to avoid cycles if widget absent
            fw = win.focusWidget()
            w = fw
            while w is not None:
                if isinstance(w, LineItemRow):
                    if hasattr(win, "items"):
                        try:
                            win.items.remove_row(w)
                        except Exception:
                            pass
                    break
                w = w.parentWidget() if hasattr(w, "parentWidget") else None
        except Exception:
            pass

    del_sc = QShortcut(Qt.Key_Delete, win)
    del_sc.activated.connect(_delete_current_row)

    # Tab order (basic through bill-to and into first item description, if available)
    win.setTabOrder(win.name_edit, win.phone_edit)
    win.setTabOrder(win.phone_edit, win.addr_edit)
    try:
        first_row = None
        if hasattr(win, "items") and hasattr(win.items, "vbox") and win.items.vbox.count() > 0:
            first_row = win.items.vbox.itemAt(0).widget()
        if first_row and hasattr(first_row, "desc_edit"):
            win.setTabOrder(win.addr_edit, first_row.desc_edit)
    except Exception:
        # If anything fails, skip customizing tab order into items
        pass


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
        is_valid = win.validate_form() if hasattr(win, 'validate_form') else True
        if not is_valid:
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
        # Ensure the save directory exists right away; fail fast with a clear message
        try:
            out_dir = _ensure_save_dir()
            if not out_dir.exists() or not out_dir.is_dir():
                raise OSError(str(out_dir))
        except Exception:
            QMessageBox.critical(win, "Cannot save", "Could not create save folder in Documents/KMC Invoices")
            return
        # Ensure settings reflect latest on-disk config
        _reload_settings_from_disk()
        logger.info("Save/Print invoked (do_print=%s)", do_print)
        is_valid = win.validate_form() if hasattr(win, 'validate_form') else True
        if not is_valid:
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
                'items': _collect_items(win),
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
            },
            'items': collected['items'],
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
            ok = False
            try:
                # Only attempt automatic printing on Windows
                import sys as _sys
                if _sys.platform == "win32":
                    ok = print_pdf(str(out_final))
                else:
                    ok = False
            except Exception:
                ok = False
            if not ok:
                QMessageBox.information(
                    win,
                    "Print",
                    "Couldn’t auto‑print. Please open the saved PDF and print from your viewer.",
                )
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
