from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QPixmap, QColor, QBrush
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QFrame,
    QLineEdit,
    QTextEdit,
    QDateEdit,

    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QDialog,
)

from app.core.currency import fmt_money, round_money
from app.core.settings import load_settings, Settings
from app.core.numbering import next_invoice_number, peek_next_invoice_number
from app.data.db import create_db_and_tables, get_session
from app.core.paths import resource_path
from app.widgets.line_items_widget import LineItemsWidget


class MainWindow(QMainWindow):
    dark_mode: bool = False

    def _recalc_total(self) -> None:
        """Compute total from line items only (no tax) and update the UI."""
        try:
            subtotal = sum(float(it.get('amount', 0.0)) for it in self.items.get_items())
        except Exception:
            subtotal = 0.0
        total = round_money(subtotal)
        self.total_value.setText(fmt_money(total))

    def __init__(self) -> None:
        super().__init__()
        QApplication.setStyle("Fusion")
        self.setWindowTitle("KMC Invoice")

        # Load settings and ensure DB exists
        self.settings: Settings = load_settings()
        create_db_and_tables()

        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Header with logo and title
        header = QHBoxLayout()
        self.logo_label = QLabel()
        # Prefer configured logo path when it exists; fallback to bundled asset; hide if none
        settings_logo = self.settings.logo_path
        default_logo_path = resource_path("assets/logo.png")
        chosen_logo = None
        if settings_logo:
            p = Path(settings_logo)
            if not p.exists():
                rp = resource_path(settings_logo)
                if rp.exists():
                    p = rp
            if p.exists():
                chosen_logo = p
        if not chosen_logo and default_logo_path.exists():
            chosen_logo = default_logo_path
        if chosen_logo and chosen_logo.exists():
            pm = QPixmap(str(chosen_logo))
            self.logo_label.setPixmap(pm.scaledToHeight(48, Qt.SmoothTransformation))
            self.logo_label.show()
        else:
            self.logo_label.hide()
        self.title_label = QLabel(self.settings.business_name or "KMC Invoice")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header.addWidget(self.logo_label)
        header.addSpacing(8)
        header.addWidget(self.title_label)
        header.addStretch(1)
        root_layout.addLayout(header)

        # Top groups: Bill To (left) and Invoice Info (right) as "cards"
        top = QHBoxLayout()
        # Ensure no extra spacer and set consistent margins/spacings
        top.setContentsMargins(12, 12, 12, 6)
        top.setSpacing(12)

        # Bill To card
        bill_card = QFrame()
        bill_card.setObjectName("Card")
        bill_card_layout = QVBoxLayout(bill_card)
        bill_card_layout.setContentsMargins(12, 12, 12, 12)
        bill_card_layout.setSpacing(10)
        bill_title = QLabel("BILL TO")
        bill_title.setObjectName("SectionTitle")
        bill_card_layout.addWidget(bill_title)
        bill_form = QFormLayout()
        bill_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bill_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.addr_edit = QTextEdit()
        self.addr_edit.setFixedHeight(70)
        name_lbl = QLabel("Name"); name_lbl.setMinimumWidth(70)
        phone_lbl = QLabel("Phone"); phone_lbl.setMinimumWidth(70)
        addr_lbl = QLabel("Address"); addr_lbl.setMinimumWidth(70)
        bill_form.addRow(name_lbl, self.name_edit)
        bill_form.addRow(phone_lbl, self.phone_edit)
        bill_form.addRow(addr_lbl, self.addr_edit)
        bill_card_layout.addLayout(bill_form)

        # Invoice Info card
        info_card = QFrame()
        info_card.setObjectName("Card")
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(12, 12, 12, 12)
        info_card_layout.setSpacing(10)
        info_title = QLabel("Invoice Info")
        info_title.setObjectName("SectionTitle")
        info_card_layout.addWidget(info_title)
        info_form = QFormLayout()
        info_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.inv_number = QLineEdit()
        self.inv_number.setReadOnly(True)
        # Auto-generate invoice number (peek only; do not increment until save)
        try:
            with get_session() as s:
                prefix = self.settings.invoice_prefix
                self.inv_number.setText(peek_next_invoice_number(prefix, s))
        except Exception:
            self.inv_number.setText(f"{self.settings.invoice_prefix}0001")

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        num_lbl = QLabel("Number"); num_lbl.setMinimumWidth(70)
        date_lbl = QLabel("Date"); date_lbl.setMinimumWidth(70)
        info_form.addRow(num_lbl, self.inv_number)
        info_form.addRow(date_lbl, self.date_edit)
        info_card_layout.addLayout(info_form)

        # Add subtle drop shadow effects
        self._apply_shadow(bill_card)
        self._apply_shadow(info_card)

        top.addWidget(bill_card, 1)
        top.addWidget(info_card, 1)
        # Align heights: ensure both cards have same minimum height
        try:
            mh = max(bill_card.sizeHint().height(), info_card.sizeHint().height())
            bill_card.setMinimumHeight(mh)
            info_card.setMinimumHeight(mh)
        except Exception:
            pass
        root_layout.addLayout(top)

        # Line items area wrapped in a Card to match upper sections
        items_card = QFrame()
        items_card.setObjectName("Card")
        items_layout = QVBoxLayout(items_card)
        items_layout.setContentsMargins(12, 12, 12, 12)
        items_layout.setSpacing(10)
        items_title = QLabel("Items")
        items_title.setObjectName("SectionTitle")
        items_layout.addWidget(items_title)

        # Use the new rows-based widget
        self.items = LineItemsWidget(self)
        self.items.totalsChanged.connect(self._update_total)
        items_layout.addWidget(self.items)

        # Table buttons (inside the card, aligned right) — only Add (rows have their own remove)
        table_btns = QHBoxLayout()
        add_btn = QPushButton("Add Row")
        table_btns.addStretch(1)
        table_btns.addWidget(add_btn)
        items_layout.addLayout(table_btns)

        root_layout.addWidget(items_card)

        # Summary bottom-right
        summary = QHBoxLayout()
        summary.addStretch(1)
        summary_box = QVBoxLayout()

        row_total = QHBoxLayout()
        total_label = QLabel("Total:")
        total_font = QFont()
        total_font.setPointSize(14)
        total_font.setBold(True)
        total_label.setFont(total_font)
        self.total_value = QLabel("0.00")
        self.total_value.setFont(total_font)
        row_total.addWidget(total_label)
        row_total.addWidget(self.total_value, 0, Qt.AlignRight)

        summary_box.addLayout(row_total)
        summary.addLayout(summary_box)
        root_layout.addLayout(summary)

        # Footer buttons (wrapped in a widget so shells can hide/replace)
        self.footer_widget = QWidget()
        footer = QHBoxLayout(self.footer_widget)
        footer.addStretch(1)
        self.btn_new_invoice = QPushButton("New Invoice")
        self.btn_save_pdf = QPushButton("Save PDF")
        self.btn_print = QPushButton("Print")
        self.btn_save_draft = QPushButton("Save Draft")
        self.btn_settings = QPushButton("Settings")
        self.btn_customers = QPushButton("Customers")
        self.btn_drafts = QPushButton("Saved Drafts")
        self.btn_all_invoices = QPushButton("All Invoices")
        # Theme toggle (QDarkStyle)
        self.btn_theme = QPushButton("Dark Mode")
        self.btn_theme.setCheckable(True)
        self.btn_theme.toggled.connect(self._on_toggle_theme)
        for b in (
            self.btn_new_invoice,
            self.btn_save_pdf,
            self.btn_print,
            self.btn_save_draft,
            self.btn_settings,
            self.btn_customers,
            self.btn_drafts,
            self.btn_all_invoices,
            self.btn_theme,
        ):
            footer.addWidget(b)
        root_layout.addWidget(self.footer_widget)

        self.setCentralWidget(root)

        # Signals
        add_btn.clicked.connect(lambda: self.items.add_row())
        self.btn_new_invoice.clicked.connect(self.new_invoice)
        self.btn_customers.clicked.connect(self.open_customers)
        self.btn_drafts.clicked.connect(self.open_drafts)
        self.btn_all_invoices.clicked.connect(self.open_all_invoices)

        # Style (light theme by default)
        self.apply_styles()

        # Seed totals from initial row
        try:
            self._update_total(0.0)
        except Exception:
            pass

    def new_invoice(self) -> None:
        """Clear form fields, reset table, set date to today, and peek next invoice number."""
        # Clear customer fields
        self.name_edit.clear()
        self.phone_edit.clear()
        self.addr_edit.clear()
        # Reset items to a single empty row
        try:
            # remove all existing rows
            while self.items.vbox.count():
                w = self.items.vbox.itemAt(0).widget()
                if w:
                    self.items.remove_row(w)
            self.items.add_row()
            self._update_total(0.0)
        except Exception:
            pass
        # Reset date to today
        try:
            self.date_edit.setDate(QDate.currentDate())
        except Exception:
            pass
        # Peek next invoice number for current prefix without incrementing
        try:
            from app.data.db import get_session
            from app.core.numbering import peek_next_invoice_number
            with get_session() as s:
                self.inv_number.setText(peek_next_invoice_number(self.settings.invoice_prefix, s))
        except Exception:
            self.inv_number.setText(f"{self.settings.invoice_prefix}0001")
        # Clear any validation styles
        if hasattr(self, '_clear_validation_styles'):
            try:
                self._clear_validation_styles()
            except Exception:
                pass

    def open_customers(self) -> None:
        try:
            from app.widgets.customers_dialog import CustomersDialog
        except Exception:
            return
        dlg = CustomersDialog(self)
        result = dlg.exec()
        if result == QDialog.Accepted and getattr(dlg, 'selected', None) is not None:
            cust = dlg.selected
            # Prefill BILL TO
            try:
                self.name_edit.setText(getattr(cust, 'name', '') or "")
                self.phone_edit.setText(getattr(cust, 'phone', '') or "")
                self.addr_edit.setPlainText(getattr(cust, 'address', '') or "")
            except Exception:
                pass

    def open_drafts(self) -> None:
        """Open the Saved Drafts dialog and load the selected invoice into the form."""
        from PySide6.QtWidgets import QMessageBox
        try:
            from app.widgets.drafts_dialog import DraftsDialog
            from app.data.repo import get_invoice_with_items
        except Exception as e:
            try:
                QMessageBox.warning(self, "Saved Drafts", f"Could not open drafts dialog.\n\nDetails: {e}")
            except Exception:
                pass
            return
        try:
            dlg = DraftsDialog(self)
            if dlg.exec() == QDialog.Accepted and getattr(dlg, 'selected_invoice_id', None):
                inv_id = int(getattr(dlg, 'selected_invoice_id'))
                data = get_invoice_with_items(inv_id)
                if not data:
                    return
                # Populate BILL TO
                cust = data.get('customer') or {}
                try:
                    self.name_edit.setText(str(cust.get('name') or ""))
                    self.phone_edit.setText(str(cust.get('phone') or ""))
                    self.addr_edit.setPlainText(str(cust.get('address') or ""))
                except Exception:
                    pass
                # Invoice basics
                inv = data.get('invoice') or {}
                try:
                    self.inv_number.setText(str(inv.get('number') or ""))
                except Exception:
                    pass
                # Date
                try:
                    d = inv.get('date')
                    if isinstance(d, _date):
                        self.date_edit.setDate(QDate(d.year, d.month, d.day))
                except Exception:
                    pass
                # Items
                try:
                    # Clear rows
                    while self.items.vbox.count():
                        w = self.items.vbox.itemAt(0).widget()
                        if w:
                            self.items.remove_row(w)
                    loaded = False
                    for it in (data.get('items') or []):
                        self.items.add_row(
                            description=str(it.get('description') or ""),
                            qty=float(it.get('qty') or 0.0),
                            rate=float(it.get('rate') or 0.0),
                        )
                        loaded = True
                    if not loaded:
                        # Keep one empty row to start with
                        self.items.add_row()
                    self._recalc_total()
                except Exception:
                    pass
        except Exception as e:
            try:
                QMessageBox.warning(self, "Saved Drafts", f"An error occurred.\n\nDetails: {e}")
            except Exception:
                pass

    def apply_styles(self) -> None:
        """Apply modern light theme via QSS."""
        ss = """
        QWidget { font-size: 13px; background: #fafafa; color: #222; }
        QMainWindow>QWidget { background: #fafafa; }
    QFrame#Card { border: 1px solid #e0e0e0; border-radius: 10px; background: #ffffff; }
    /* Row mini-card inside Items */
    QFrame#CardRow { border:1px solid #e0e0e0; border-radius:10px; background:#fff; padding:6px; }
    QFrame#CardRow:focus-within { border-color:#5b8def; }
    QLabel#SectionTitle { font-size: 14px; font-weight: 700; color: #333; padding: 2px 2px 0 2px; }
        QLabel { font-size: 13px; }
    /* (removed table header styles) */
        /* Inputs: make them consistent with card styling */
        QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox {
            border: 1px solid #cfcfcf; border-radius: 8px; padding: 8px; background: #ffffff;
        }
        /* Requested overrides */
        QLineEdit, QDateEdit, QDoubleSpinBox { border:1px solid #cfcfcf; border-radius:10px; padding:8px; background:#fff; }
    QDateEdit::drop-down { width: 20px; }
    QDateEdit::down-button, QDateEdit::up-button { width: 16px; }
    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus { border: 1px solid #5b8def; }
    /* Requested overrides */
    QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus { border-color:#5b8def; }
        QPushButton {
            padding: 9px 16px; border-radius: 10px; border: 1px solid #d0d0d0; background: #ffffff;
        }
        QPushButton:hover { background: #f3f6ff; border-color: #b8c6ff; }
        QPushButton:pressed { background: #e8eeff; }
        """
        # Clear any global stylesheet (if dark mode was previously active)
        app = QApplication.instance()
        if app:
            app.setStyleSheet("")
        self.setStyleSheet(ss)

    def apply_dark_styles(self) -> None:
        """Apply modern dark theme via QSS (pairs with optional qdarkstyle)."""
        ss = """
        QWidget { font-size: 13px; background: #2b2b2b; color: #f0f0f0; }
        QMainWindow>QWidget { background: #2b2b2b; }
    QFrame#Card { border: 1px solid #3d3d3d; border-radius: 10px; background: #2f2f2f; }
    /* Row mini-card inside Items */
    QFrame#CardRow { border:1px solid #555; border-radius:10px; background:#3a3a3a; }
    QFrame#CardRow:focus-within { border-color: #7aa2ff; }
    QLabel#SectionTitle { font-size: 14px; font-weight: 700; color: #f0f0f0; padding: 2px 2px 0 2px; }
        QLabel { font-size: 13px; color: #f0f0f0; }
    /* Removed table header styles */
        QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox {
            border: 1px solid #555; border-radius: 8px; padding: 8px; background: #3a3a3a; color: #f0f0f0;
            selection-background-color: #5b8def; selection-color: #ffffff;
        }
        /* Requested overrides */
        QLineEdit, QDateEdit, QDoubleSpinBox { border:1px solid #666; border-radius:10px; padding:8px; background:#2e2e2e; color:#f0f0f0; }
    QDateEdit::drop-down { width: 20px; }
    QDateEdit::down-button, QDateEdit::up-button { width: 16px; }
    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus { border: 1px solid #7aa2ff; }
    /* Requested overrides */
    QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus { border-color:#8cb0ff; }
        QPushButton {
            padding: 9px 16px; border-radius: 10px; border: 1px solid #555; background: #3a3a3a; color: #f0f0f0;
        }
        QPushButton:hover { background: #414141; border-color: #6a6a6a; }
        QPushButton:pressed { background: #3c3c3c; }
        """
        # Layer our dark QSS, optionally on top of qdarkstyle (if applied at app level)
        self.setStyleSheet(ss)

    def _apply_shadow(self, widget: QWidget) -> None:
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(16)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 40))
            widget.setGraphicsEffect(shadow)
        except Exception:
            pass

    def _on_toggle_theme(self, checked: bool) -> None:
        self.dark_mode = bool(checked)
        app = QApplication.instance()
        if self.dark_mode:
            # Optionally apply qdarkstyle at app level, then layer our dark QSS
            try:
                import qdarkstyle  # type: ignore
                if app:
                    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
            except Exception:
                # If qdarkstyle not available, ensure no app-level style conflicts
                if app:
                    app.setStyleSheet("")
            self.apply_dark_styles()
        else:
            # Clear any app-level stylesheet and apply our light theme
            if app:
                app.setStyleSheet("")
            self.apply_styles()

    def _update_total(self, subtotal: float) -> None:
        """Update only the total value label from current items (no subtotal UI)."""
        total = round_money(subtotal)
        self.total_value.setText(fmt_money(total))

    def collect_data(self) -> dict:
        """Collect form data for DB save and PDF build.

                Returns dict with keys:
                    customer: {name, phone, address}
                    invoice: {number, date (datetime.date)}
                    items: [{description, qty, rate, amount}]
                    total
        """
        # Invoice basics
        qd = self.date_edit.date()
        inv_date = _date(qd.year(), qd.month(), qd.day())

        # Items
        items = []
        try:
            items = self.items.get_items()
        except Exception:
            pass

        subtotal = round_money(sum(i['amount'] for i in items))
        total = round_money(subtotal)

        return {
            'customer': {
                'name': self.name_edit.text().strip(),
                'phone': self.phone_edit.text().strip(),
                'address': self.addr_edit.toPlainText().strip(),
            },
            'invoice': {
                'number': self.inv_number.text().strip(),
                'date': inv_date,
            },
            'items': items,
            'total': float(total),
        }

    def refresh_settings(self, settings: Settings) -> None:
        """Apply new settings to UI: logo, title, and invoice prefix."""
        self.settings = settings
        # Update header title and logo
        self.title_label.setText(self.settings.business_name or "KMC Invoice")
        default_logo_path = resource_path("assets/logo.png")
        chosen_logo = None
        if self.settings.logo_path:
            p = Path(self.settings.logo_path)
            if not p.exists():
                rp = resource_path(self.settings.logo_path)
                if rp.exists():
                    p = rp
            if p.exists():
                chosen_logo = p
        if not chosen_logo and default_logo_path.exists():
            chosen_logo = default_logo_path
        if chosen_logo and chosen_logo.exists():
            pm = QPixmap(str(chosen_logo))
            self.logo_label.setPixmap(pm.scaledToHeight(48, Qt.SmoothTransformation))
            self.logo_label.show()
        else:
            self.logo_label.clear()
            self.logo_label.hide()
        # Update invoice number for new prefix (peek only)
        try:
            from app.data.db import get_session
            from app.core.numbering import peek_next_invoice_number
            with get_session() as s:
                self.inv_number.setText(peek_next_invoice_number(self.settings.invoice_prefix, s))
        except Exception:
            self.inv_number.setText(f"{self.settings.invoice_prefix}0001")
        # Recalculate total (no tax in UI)
        self._recalc_total()
        # Apply compact mode tweaks (lighter spacing/font) without changing layout structure
        try:
            if bool(getattr(self.settings, 'compact_mode', False)):
                self.setStyleSheet(self.styleSheet().replace('font-size: 13px', 'font-size: 12px'))
            else:
                # Reapply base style to reset any compact overrides
                if self.dark_mode:
                    self.apply_dark_styles()
                else:
                    self.apply_styles()
        except Exception:
            pass

    # --- Validation helpers ---
    def _clear_validation_styles(self) -> None:
        # Reset edits
        for w in (self.name_edit, self.phone_edit, self.addr_edit):
            w.setStyleSheet("")
        # Reset per-row editor styles in LineItemsWidget
        try:
            count = self.items.vbox.count()
            for i in range(count):
                roww = self.items.vbox.itemAt(i).widget()
                if not roww:
                    continue
                for attr in ("desc_edit", "qty_spin", "rate_spin"):
                    ed = getattr(roww, attr, None)
                    if ed and hasattr(ed, "setStyleSheet"):
                        ed.setStyleSheet("")
        except Exception:
            pass

    def _mark_field_invalid(self, widget) -> None:
        try:
            # Light red background and subtle border
            widget.setStyleSheet("background-color: #ffecec; border: 1px solid #e07070;")
        except Exception:
            pass

    def validate_form(self) -> bool:
        """Validate required fields and highlight invalid cells.

        Returns True when valid; otherwise shows a single dialog with all issues and returns False.
        """
        self._clear_validation_styles()
        issues: list[str] = []

        # Required: Customer name
        if not self.name_edit.text().strip():
            self.name_edit.setStyleSheet("border: 1px solid #e07070;")
            issues.append("Customer name is required.")

        # Validate line items (new widget)
        valid_row_found = False
        try:
            count = self.items.vbox.count()
        except Exception:
            count = 0
        for i in range(count):
            roww = self.items.vbox.itemAt(i).widget()
            if not roww:
                continue
            desc = getattr(roww, "desc_edit", None)
            qty = getattr(roww, "qty_spin", None)
            rate = getattr(roww, "rate_spin", None)
            desc_text = (desc.text().strip() if desc else "")
            try:
                qty_val = float(qty.value()) if qty else 0.0
            except Exception:
                qty_val = 0.0
            try:
                rate_val = float(rate.value()) if rate else 0.0
            except Exception:
                rate_val = 0.0

            is_empty = (desc_text == "" and qty_val == 0.0 and rate_val == 0.0)
            if is_empty:
                continue

            row_ok = True
            if not desc_text and desc:
                self._mark_field_invalid(desc)
                issues.append(f"Row {i+1}: Description is required.")
                row_ok = False
            if qty is None or qty_val <= 0:
                if qty:
                    self._mark_field_invalid(qty)
                issues.append(f"Row {i+1}: Qty must be > 0.")
                row_ok = False
            if rate is None or rate_val <= 0:
                if rate:
                    self._mark_field_invalid(rate)
                issues.append(f"Row {i+1}: Rate must be > 0.")
                row_ok = False

            valid_row_found = valid_row_found or row_ok

        if not valid_row_found:
            issues.append("At least one valid line item is required (description, qty > 0, rate > 0).")

        if issues:
            from PySide6.QtWidgets import QMessageBox
            try:
                QMessageBox.warning(self, "Fix form errors", "\n".join(f"• {m}" for m in issues))
            except Exception:
                pass
            return False
        return True

    def open_all_invoices(self) -> None:
        from PySide6.QtWidgets import QMessageBox, QDialog
        try:
            from app.widgets.invoices_dialog import InvoicesDialog
            from app.data.repo import get_invoice_with_items
        except Exception as e:
            try:
                QMessageBox.warning(self, "All Invoices", f"Could not open invoices dialog.\n\nDetails: {e}")
            except Exception:
                pass
            return
        try:
            dlg = InvoicesDialog(self)
            if dlg.exec() == QDialog.Accepted and getattr(dlg, 'selected_invoice_id', None):
                inv_id = int(getattr(dlg, 'selected_invoice_id'))
                data = get_invoice_with_items(inv_id)
                if not data:
                    return
                # Populate BILL TO
                cust = data.get('customer') or {}
                try:
                    self.name_edit.setText(str(cust.get('name') or ""))
                    self.phone_edit.setText(str(cust.get('phone') or ""))
                    self.addr_edit.setPlainText(str(cust.get('address') or ""))
                except Exception:
                    pass
                # Invoice basics
                inv = data.get('invoice') or {}
                try:
                    self.inv_number.setText(str(inv.get('number') or ""))
                except Exception:
                    pass
                # Date
                try:
                    d = inv.get('date')
                    if isinstance(d, _date):
                        self.date_edit.setDate(QDate(d.year, d.month, d.day))
                except Exception:
                    pass
                # Items
                try:
                    while self.items.vbox.count():
                        w = self.items.vbox.itemAt(0).widget()
                        if w:
                            self.items.remove_row(w)
                    loaded = False
                    for it in (data.get('items') or []):
                        self.items.add_row(
                            description=str(it.get('description') or ""),
                            qty=float(it.get('qty') or 0.0),
                            rate=float(it.get('rate') or 0.0),
                        )
                        loaded = True
                    if not loaded:
                        self.items.add_row()
                    self._recalc_total()
                except Exception:
                    pass
        except Exception as e:
            try:
                QMessageBox.warning(self, "All Invoices", f"An error occurred.\n\nDetails: {e}")
            except Exception:
                pass


def create_main_window() -> QMainWindow:
    """Factory used by main.py. Returns the new shell AppWindow wrapping the editor."""
    try:
        from app.shell import create_app_window
        return create_app_window()
    except Exception:
        # Fallback to legacy single-window editor if shell cannot be created
        return MainWindow()

    
    

    
    

