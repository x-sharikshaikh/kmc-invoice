from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QPixmap, QColor, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QTextEdit,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
)

from app.core.currency import fmt_money, round_money
from app.core.settings import load_settings, Settings
from app.core.numbering import next_invoice_number
from app.data.db import create_db_and_tables, get_session


class MainWindow(QMainWindow):
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
        logo_label = QLabel()
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "logo.png"
        if logo_path.exists():
            pm = QPixmap(str(logo_path))
            logo_label.setPixmap(pm.scaledToHeight(48, Qt.SmoothTransformation))
        title = QLabel("KMC Invoice")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(logo_label)
        header.addSpacing(8)
        header.addWidget(title)
        header.addStretch(1)
        root_layout.addLayout(header)

        # Top groups: Bill To (left) and Invoice Info (right)
        top = QHBoxLayout()

        bill_group = QGroupBox("BILL TO")
        bill_form = QFormLayout(bill_group)
        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.addr_edit = QTextEdit()
        self.addr_edit.setFixedHeight(70)
        bill_form.addRow("Name", self.name_edit)
        bill_form.addRow("Phone", self.phone_edit)
        bill_form.addRow("Address", self.addr_edit)

        info_group = QGroupBox("Invoice Info")
        info_form = QFormLayout(info_group)
        self.inv_number = QLineEdit()
        self.inv_number.setReadOnly(True)
        # Auto-generate invoice number
        try:
            with get_session() as s:
                prefix = self.settings.invoice_prefix
                self.inv_number.setText(next_invoice_number(prefix, s))
        except Exception:
            self.inv_number.setText(f"{self.settings.invoice_prefix}0001")

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(QDate.currentDate())
        info_form.addRow("Number", self.inv_number)
        info_form.addRow("Date", self.date_edit)

        top.addWidget(bill_group, 1)
        top.addWidget(info_group, 1)
        root_layout.addLayout(top)

        # Line items table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Sl.", "Description", "Qty", "Rate", "Amount"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
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
        self.btn_save_pdf = QPushButton("Save PDF")
        self.btn_print = QPushButton("Print")
        self.btn_save_draft = QPushButton("Save Draft")
        self.btn_settings = QPushButton("Settings")
        for b in (self.btn_save_pdf, self.btn_print, self.btn_save_draft, self.btn_settings):
            footer.addWidget(b)
        root_layout.addLayout(footer)

        self.setCentralWidget(root)

        # Signals
        add_btn.clicked.connect(self.add_row)
        rm_btn.clicked.connect(self.remove_selected_rows)
        self.table.itemChanged.connect(self.on_item_changed)

        # Style
        self.apply_styles()

        # Seed with one empty row
        self.add_row()
        self._recalc_subtotal_tax_total()

    def apply_styles(self) -> None:
        ss = """
        QWidget { font-size: 13px; }
        QGroupBox { font-size: 14px; font-weight: 600; border: 1px solid #ccc; border-radius: 8px; margin-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; top: -8px; padding: 0 4px; background: palette(window); }
        QLabel { font-size: 13px; }
        QHeaderView::section { font-size: 14px; padding: 6px; }
        QLineEdit, QTextEdit, QDateEdit, QTableWidget { border: 1px solid #bbb; border-radius: 6px; padding: 6px; }
        QPushButton { padding: 8px 14px; border-radius: 6px; }
        QPushButton:hover { background: #f0f0f0; }
        """
        self.setStyleSheet(ss)

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

