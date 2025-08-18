from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame
)

from app.styles.themes import light_qss, dark_qss
from app.ui_main import MainWindow as InvoiceEditor


class NavRail(QWidget):
    navigate = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavRail")
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 12, 8, 12)
        v.setSpacing(4)

        def make_btn(text: str, idx: int) -> QPushButton:
            b = QPushButton(text)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.clicked.connect(lambda: self.navigate.emit(idx))
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(32)
            return b

        self.btn_invoice = make_btn("Invoice", 0)
        self.btn_invoices = make_btn("Invoices", 1)
        self.btn_customers = make_btn("Customers", 2)
        self.btn_items = make_btn("Items", 3)
        self.btn_settings = make_btn("Settings", 4)
        for b in [self.btn_invoice, self.btn_invoices, self.btn_customers, self.btn_items, self.btn_settings]:
            v.addWidget(b)
        v.addStretch(1)
        self.buttons = [self.btn_invoice, self.btn_invoices, self.btn_customers, self.btn_items, self.btn_settings]
        self.select(0)

    def select(self, idx: int) -> None:
        for i, b in enumerate(self.buttons):
            b.setChecked(i == idx)


class FooterBar(QWidget):
    def __init__(self, editor: InvoiceEditor, parent: Optional[Widget] = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self.setObjectName("FooterBar")
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 8, 12, 8)
        h.addStretch(1)
        # Preview button added by shell
        self.btn_preview = QPushButton("Preview")
        # Reuse editor's existing actions to avoid breaking business logic
        for b in (editor.btn_new_invoice, self.btn_preview, editor.btn_save_pdf, editor.btn_print, editor.btn_save_draft, editor.btn_settings):
            h.addWidget(b)


class AppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("KMC Invoice")

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        title = QLabel("KMC Invoice")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        title.setFont(f)
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        # Body: Nav rail + routed views
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.nav = NavRail()
        self.nav.navigate.connect(self._on_nav)
        body.addWidget(self.nav)

        self.stack = QStackedWidget()
        # View 0: Invoice editor (wrap existing MainWindow central widget)
        self.invoice_editor = InvoiceEditor()
        # Grab editor central widget and embed into our stack
        self.invoice_view = self.invoice_editor.centralWidget()
        self.invoice_editor.setCentralWidget(QWidget())  # detach
        # Hide the original footer inside the embedded editor; we render our footer bar
        try:
            if hasattr(self.invoice_editor, 'footer_widget') and self.invoice_editor.footer_widget is not None:
                self.invoice_editor.footer_widget.hide()
        except Exception:
            pass
        self.stack.addWidget(self.invoice_view)
        # Additional views: invoices and customers (items/settings are placeholders)
        from app.views.invoices_view import InvoicesView
        from app.views.customers_view import CustomersView
        from app.views.placeholders import placeholder
        self.invoices_view = InvoicesView(); self.stack.addWidget(self.invoices_view)
        self.customers_view = CustomersView(); self.stack.addWidget(self.customers_view)
        self.items_view = placeholder("Items"); self.stack.addWidget(self.items_view)
        self.settings_view = placeholder("Settings"); self.stack.addWidget(self.settings_view)
        # Wire activations
        try:
            self.invoices_view.invoiceActivated.connect(self._on_invoice_activated)
        except Exception:
            pass
        try:
            # Double-click on a customer row prefills Bill To
            self.customers_view.table.itemDoubleClicked.connect(lambda _it: self._on_customer_row_activated())
        except Exception:
            pass

        body.addWidget(self.stack, 1)
        layout.addLayout(body, 1)

        # Sticky footer uses editor's action buttons
        self.footer = FooterBar(self.invoice_editor)
        layout.addWidget(self.footer)

        self.setCentralWidget(root)
        # Default theme (light)
        self.apply_light_theme()

        # Expose some of editor's API so main.py works unchanged
        self.btn_new_invoice = self.invoice_editor.btn_new_invoice
        self.btn_save_pdf = self.invoice_editor.btn_save_pdf
        self.btn_print = self.invoice_editor.btn_print
        self.btn_save_draft = self.invoice_editor.btn_save_draft
        self.btn_settings = self.invoice_editor.btn_settings
        self.btn_preview = self.footer.btn_preview
        self.items = self.invoice_editor.items
        self.name_edit = self.invoice_editor.name_edit
        self.phone_edit = self.invoice_editor.phone_edit
        self.addr_edit = self.invoice_editor.addr_edit
        self.inv_number = self.invoice_editor.inv_number
        self.date_edit = self.invoice_editor.date_edit
        self.validate_form = self.invoice_editor.validate_form
        self.collect_data = self.invoice_editor.collect_data
        self.refresh_settings = self.invoice_editor.refresh_settings

    def _on_nav(self, idx: int) -> None:
        self.nav.select(idx)
        self.stack.setCurrentIndex(idx)
        # Refresh list views when shown
        try:
            if idx == 1 and hasattr(self, 'invoices_view'):
                self.invoices_view.refresh()
            elif idx == 2 and hasattr(self, 'customers_view'):
                self.customers_view.refresh()
        except Exception:
            pass

    def _on_invoice_activated(self, inv_id: int) -> None:
        """Load the selected invoice into the editor and switch to Invoice view."""
        try:
            from app.data.repo import get_invoice_with_items
        except Exception:
            return
        try:
            data = get_invoice_with_items(int(inv_id))
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
                from datetime import date as _date
                from PySide6.QtCore import QDate
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
                    self.items.add_row()
                # Recalculate totals
                try:
                    self.validate_form(); self.collect_data();  # no-op with side-effects for consistency
                except Exception:
                    pass
            except Exception:
                pass
            # Switch to editor view
            self._on_nav(0)
        except Exception:
            pass

    def _on_customer_row_activated(self) -> None:
        """Prefill Bill To from the selected customer and switch to Invoice view."""
        try:
            r = self.customers_view.table.currentRow()
            if r < 0:
                return
            c = self.customers_view._data[r] if r < len(getattr(self.customers_view, '_data', [])) else None
            if not c:
                return
            try:
                self.name_edit.setText(getattr(c, 'name', '') or "")
                self.phone_edit.setText(getattr(c, 'phone', '') or "")
                self.addr_edit.setPlainText(getattr(c, 'address', '') or "")
            except Exception:
                pass
            self._on_nav(0)
        except Exception:
            pass

    # Theme helpers
    def apply_light_theme(self) -> None:
        self.setStyleSheet(light_qss())

    def apply_dark_theme(self) -> None:
        self.setStyleSheet(dark_qss())


def create_app_window() -> AppWindow:
    return AppWindow()
