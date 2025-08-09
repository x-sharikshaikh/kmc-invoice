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
    QHeaderView,
    QLineEdit,
    QTextEdit,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
)

from app.core.currency import fmt_money, round_money
from app.core.settings import load_settings, Settings
from app.core.numbering import next_invoice_number, peek_next_invoice_number
from app.data.db import create_db_and_tables, get_session
from app.core.paths import resource_path


class LineItemDelegate(QStyledItemDelegate):
    """Inset, styled editors for table cells to match card inputs."""
    def __init__(self, parent=None, inset: int = 6):
        super().__init__(parent)
        self._inset = inset

    def createEditor(self, parent, option, index):
        ed = QLineEdit(parent)
        ed.setObjectName("CellEditor")
        # Right-align numeric columns (Qty=2, Rate=3)
        if index.column() in (2, 3):
            ed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return ed

    def updateEditorGeometry(self, editor, option, index):
        r = option.rect.adjusted(self._inset, self._inset, -self._inset, -self._inset)
        editor.setGeometry(r)


class MainWindow(QMainWindow):
    dark_mode: bool = False

    def _recalc_subtotal_tax_total(self) -> None:
        sub = 0.0
        rows = self.table.rowCount()
        for r in range(rows):
            item = self.table.item(r, 4)
            try:
                sub += float(item.text()) if item and item.text() else 0.0
            except Exception:
                pass
        tax = round_money(sub * float(self.settings.tax_rate))
        total = round_money(sub + tax)
        self.subtotal_value.setText(fmt_money(sub))
        self.tax_value.setText(fmt_money(tax))
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
        root_layout.addLayout(top)

        # Line items table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Sl.", "Description", "Qty", "Rate", "Amount"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        # Ensure comfortable row height so text/editors aren't clipped
        try:
            self.table.verticalHeader().setDefaultSectionSize(40)
        except Exception:
            pass
        # Use delegate with insets so editors don't touch cell borders
        self.table.setItemDelegate(LineItemDelegate(self.table, inset=6))
        # Column sizing: let Description take the remaining space, others fit to contents
        try:
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        except Exception:
            pass
        # Center and bold header text
        try:
            self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        except Exception:
            pass
        root_layout.addWidget(self.table)

        # Table buttons
        table_btns = QHBoxLayout()
        add_btn = QPushButton("Add Row")
        rm_btn = QPushButton("Remove Row")
        table_btns.addStretch(1)
        table_btns.addWidget(add_btn)
        table_btns.addWidget(rm_btn)
        root_layout.addLayout(table_btns)

        # Summary bottom-right
        summary = QHBoxLayout()
        summary.addStretch(1)
        summary_box = QVBoxLayout()

        row_sub = QHBoxLayout()
        row_sub.addWidget(QLabel("Subtotal:"))
        self.subtotal_value = QLabel("0.00")
        row_sub.addWidget(self.subtotal_value, 0, Qt.AlignRight)

        row_tax = QHBoxLayout()
        row_tax.addWidget(QLabel("Tax:"))
        self.tax_value = QLabel("0.00")
        row_tax.addWidget(self.tax_value, 0, Qt.AlignRight)

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

        summary_box.addLayout(row_sub)
        summary_box.addLayout(row_tax)
        summary_box.addLayout(row_total)
        summary.addLayout(summary_box)
        root_layout.addLayout(summary)

        # Footer buttons
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_new_invoice = QPushButton("New Invoice")
        self.btn_save_pdf = QPushButton("Save PDF")
        self.btn_print = QPushButton("Print")
        self.btn_save_draft = QPushButton("Save Draft")
        self.btn_settings = QPushButton("Settings")
        self.btn_customers = QPushButton("Customers")
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
            self.btn_theme,
        ):
            footer.addWidget(b)
        root_layout.addLayout(footer)

        self.setCentralWidget(root)

        # Signals
        add_btn.clicked.connect(self.add_row)
        rm_btn.clicked.connect(self.remove_selected_rows)
        self.table.itemChanged.connect(self.on_item_changed)
        self.btn_new_invoice.clicked.connect(self.new_invoice)
        self.btn_customers.clicked.connect(self.open_customers)

        # Style (light theme by default)
        self.apply_styles()

        # Seed with one empty row
        self.add_row()
        self._recalc_subtotal_tax_total()

    def new_invoice(self) -> None:
        """Clear form fields, reset table, set date to today, and peek next invoice number."""
        # Clear customer fields
        self.name_edit.clear()
        self.phone_edit.clear()
        self.addr_edit.clear()
        # Reset table to a single empty row
        self.table.setRowCount(0)
        self.add_row()
        # Reset totals
        self._recalc_subtotal_tax_total()
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
        if dlg.exec() == dlg.Accepted and dlg.selected is not None:
            cust = dlg.selected
            # Prefill BILL TO
            try:
                self.name_edit.setText(cust.name or "")
                self.phone_edit.setText(cust.phone or "")
                self.addr_edit.setPlainText(cust.address or "")
            except Exception:
                pass

    def apply_styles(self) -> None:
        """Apply modern light theme via QSS."""
        ss = """
        QWidget { font-size: 13px; background: #fafafa; color: #222; }
        QMainWindow>QWidget { background: #fafafa; }
    QFrame#Card { border: 1px solid #e0e0e0; border-radius: 10px; background: #ffffff; }
    QLabel#SectionTitle { font-size: 14px; font-weight: 700; color: #333; padding: 0 2px 2px 2px; }
        QLabel { font-size: 13px; }
        QHeaderView::section {
            font-size: 14px; padding: 8px; font-weight: 600; background: #f2f2f2; border: 0px; border-bottom: 1px solid #ddd;
        }
        QTableWidget { border: 1px solid #e0e0e0; border-radius: 10px; background: #ffffff; gridline-color: #ececec; }
        QTableView { outline: 0; }
        QTableView::item:focus { outline: none; }
        QTableWidget::item { padding: 6px 8px; }
        /* Make in-cell editors (e.g., Description) match card inputs */
        QLineEdit#CellEditor {
            padding: 8px 12px; min-height: 30px; border: 1px solid #cfcfcf; border-radius: 10px;
            background: #ffffff; color: #222;
        }
        QLineEdit#CellEditor:focus { border: 1px solid #5b8def; }
        /* Keep selection subtle so the rounded editor stands out */
        QTableView::item:selected { background: transparent; }
        QLineEdit, QTextEdit, QDateEdit {
            border: 1px solid #cfcfcf; border-radius: 10px; padding: 8px; background: #ffffff;
        }
    QDateEdit::drop-down { width: 20px; }
    QDateEdit::down-button, QDateEdit::up-button { width: 16px; }
        QLineEdit:focus, QTextEdit:focus, QDateEdit:focus { border: 1px solid #5b8def; }
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
    QLabel#SectionTitle { font-size: 14px; font-weight: 700; color: #f0f0f0; padding: 0 2px 2px 2px; }
        QLabel { font-size: 13px; color: #f0f0f0; }
        QHeaderView::section {
            font-size: 14px; padding: 8px; font-weight: 600; background: #3a3a3a; border: 0px; border-bottom: 1px solid #444;
            color: #f0f0f0;
        }
        QTableWidget { border: 1px solid #3d3d3d; border-radius: 10px; background: #2f2f2f; gridline-color: #444; }
        QTableView { outline: 0; }
        QTableView::item:focus { outline: none; }
        QTableWidget::item { padding: 6px 8px; }
        /* Dark in-cell editors styling to match card inputs */
        QLineEdit#CellEditor {
            padding: 8px 12px; min-height: 30px; border: 1px solid #666; border-radius: 10px;
            background: #3a3a3a; color: #f0f0f0;
        }
        QLineEdit#CellEditor:focus { border: 1px solid #7aa2ff; }
        QTableView::item:selected { background: transparent; }
        QLineEdit, QTextEdit, QDateEdit {
            border: 1px solid #555; border-radius: 10px; padding: 8px; background: #3a3a3a; color: #f0f0f0;
            selection-background-color: #5b8def; selection-color: #ffffff;
        }
    QDateEdit::drop-down { width: 20px; }
    QDateEdit::down-button, QDateEdit::up-button { width: 16px; }
        QLineEdit:focus, QTextEdit:focus, QDateEdit:focus { border: 1px solid #7aa2ff; }
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

    def add_row(self) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        # Sl.
        sl = QTableWidgetItem(str(r + 1))
        sl.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table.setItem(r, 0, sl)
        # Description
        self.table.setItem(r, 1, QTableWidgetItem(""))
        # Qty
        self.table.setItem(r, 2, QTableWidgetItem("0"))
        # Rate
        self.table.setItem(r, 3, QTableWidgetItem("0.00"))
        # Amount (read-only)
        amt = QTableWidgetItem("0.00")
        amt.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table.setItem(r, 4, amt)

    def remove_selected_rows(self) -> None:
        selected = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in selected:
            self.table.removeRow(r)
        # Renumber Sl.
        for i in range(self.table.rowCount()):
            it = self.table.item(i, 0)
            if it:
                it.setText(str(i + 1))
        self._recalc_subtotal_tax_total()

    def on_item_changed(self, item: QTableWidgetItem) -> None:
        r, c = item.row(), item.column()
        if c in (2, 3, 1):  # qty or rate or description
            try:
                qty = float(self.table.item(r, 2).text()) if self.table.item(r, 2) else 0.0
                rate = float(self.table.item(r, 3).text()) if self.table.item(r, 3) else 0.0
                amt_val = round_money(qty * rate)
            except Exception:
                amt_val = 0.0
            # Set amount without re-triggering
            self.table.blockSignals(True)
            if self.table.item(r, 4) is None:
                self.table.setItem(r, 4, QTableWidgetItem(fmt_money(amt_val)))
            else:
                self.table.item(r, 4).setText(fmt_money(amt_val))
            self.table.blockSignals(False)
            self._recalc_subtotal_tax_total()

    def collect_data(self) -> dict:
        """Collect form data for DB save and PDF build.

        Returns dict with keys:
          customer: {name, phone, address}
          invoice: {number, date (datetime.date)}
          items: [{description, qty, rate, amount}]
          subtotal, tax, total
        """
        # Invoice basics
        qd = self.date_edit.date()
        inv_date = _date(qd.year(), qd.month(), qd.day())

        # Items
        items: list[dict] = []
        rows = self.table.rowCount()
        for r in range(rows):
            desc_it = self.table.item(r, 1)
            qty_it = self.table.item(r, 2)
            rate_it = self.table.item(r, 3)
            amt_it = self.table.item(r, 4)
            def _f(it):
                try:
                    return float(it.text()) if it and it.text() else 0.0
                except Exception:
                    return 0.0
            items.append({
                'description': (desc_it.text() if desc_it else '').strip(),
                'qty': _f(qty_it),
                'rate': _f(rate_it),
                'amount': _f(amt_it),
            })

        subtotal = round_money(sum(i['amount'] for i in items))
        tax = round_money(subtotal * float(self.settings.tax_rate))
        total = round_money(subtotal + tax)

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
            'subtotal': float(subtotal),
            'tax': float(tax),
            'total': float(total),
        }

    def refresh_settings(self, settings: Settings) -> None:
        """Apply new settings to UI: logo, title, tax rate effects, invoice prefix."""
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
        # Recalculate totals to reflect new tax rate
        self._recalc_subtotal_tax_total()

    # --- Validation helpers ---
    def _clear_validation_styles(self) -> None:
        # Reset edits
        for w in (self.name_edit, self.phone_edit, self.addr_edit):
            w.setStyleSheet("")
        # Reset table cell backgrounds for Description/Qty/Rate
        rows = self.table.rowCount()
        for r in range(rows):
            for c in (1, 2, 3):
                it = self.table.item(r, c)
                if it:
                    it.setBackground(QBrush())

    def _mark_cell_invalid(self, row: int, col: int) -> None:
        it = self.table.item(row, col)
        if not it:
            it = QTableWidgetItem("")
            self.table.setItem(row, col, it)
        it.setBackground(QColor(255, 230, 230))  # light red

    def validate_form(self) -> list[str]:
        """Validate required fields and highlight invalid cells. Returns issue strings."""
        self._clear_validation_styles()
        issues: list[str] = []

        # Required: Customer name
        if not self.name_edit.text().strip():
            self.name_edit.setStyleSheet("border: 1px solid #e07070;")
            issues.append("Customer name is required.")

        # Validate line items
        rows = self.table.rowCount()
        valid_row_found = False
        for r in range(rows):
            desc = (self.table.item(r, 1).text().strip() if self.table.item(r, 1) else "")
            qty_text = (self.table.item(r, 2).text().strip() if self.table.item(r, 2) else "")
            rate_text = (self.table.item(r, 3).text().strip() if self.table.item(r, 3) else "")

            # Consider row empty if all blank/zero
            def _to_float(t: str) -> float | None:
                try:
                    return float(t) if t != "" else 0.0
                except Exception:
                    return None

            qty = _to_float(qty_text)
            rate = _to_float(rate_text)

            is_empty = (desc == "" and (qty_text == "" or qty == 0.0) and (rate_text == "" or rate == 0.0))
            if is_empty:
                continue

            row_ok = True
            if not desc:
                self._mark_cell_invalid(r, 1)
                issues.append(f"Row {r+1}: Description is required.")
                row_ok = False
            if qty is None:
                self._mark_cell_invalid(r, 2)
                issues.append(f"Row {r+1}: Qty must be a number.")
                row_ok = False
            elif qty <= 0:
                self._mark_cell_invalid(r, 2)
                issues.append(f"Row {r+1}: Qty must be > 0.")
                row_ok = False
            if rate is None:
                self._mark_cell_invalid(r, 3)
                issues.append(f"Row {r+1}: Rate must be a number.")
                row_ok = False
            elif rate <= 0:
                self._mark_cell_invalid(r, 3)
                issues.append(f"Row {r+1}: Rate must be > 0.")
                row_ok = False

            valid_row_found = valid_row_found or row_ok

        if not valid_row_found:
            issues.append("At least one valid line item is required (description, qty > 0, rate > 0).")

        return issues


def create_main_window() -> QMainWindow:
    return MainWindow()

