from __future__ import annotations

from typing import Optional
from datetime import date as _date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QDateEdit,
    QMessageBox,
)

from app.data.repo import list_invoices_between, delete_invoice


class InvoicesDialog(QDialog):
    """All invoices listing with search and date range."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("All Invoices")
        self.resize(820, 520)
        self.setModal(True)

        root = QVBoxLayout(self)

        # Filters row: date range + search
        top = QHBoxLayout()
        top.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd-MM-yyyy")
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        top.addWidget(self.from_date)

        top.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("dd-MM-yyyy")
        self.to_date.setDate(QDate.currentDate())
        top.addWidget(self.to_date)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search number or customer…")
        top.addWidget(self.search_edit, 1)

        self.btn_search = QPushButton("Search")
        self.btn_use = QPushButton("Use Selected")
        self.btn_open_pdf = QPushButton("Open PDF")
        self.btn_delete = QPushButton("Delete")
        top.addWidget(self.btn_search)
        top.addStretch(1)
        top.addWidget(self.btn_use)
        top.addWidget(self.btn_open_pdf)
        top.addWidget(self.btn_delete)
        root.addLayout(top)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Number", "Date", "Customer", "Phone", "Total"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        # Wire
        self.btn_search.clicked.connect(self._do_search)
        self.search_edit.returnPressed.connect(self._do_search)
        self.table.itemDoubleClicked.connect(lambda _it: self._use_selected())
        self.btn_use.clicked.connect(self._use_selected)
        self.btn_open_pdf.clicked.connect(self._open_pdf)
        self.btn_delete.clicked.connect(self._delete_selected)

        # State for result
        self.selected_invoice_id: Optional[int] = None

        # Initial
        self._do_search()

    def _current_invoice_id(self) -> Optional[int]:
        r = self.table.currentRow()
        if r < 0:
            return None
        it = self.table.item(r, 0)
        try:
            return int(it.data(Qt.UserRole)) if it is not None else None
        except Exception:
            return None

    def _do_search(self) -> None:
        qs = self.search_edit.text().strip()
        fd = self.from_date.date(); td = self.to_date.date()
        start = _date(fd.year(), fd.month(), fd.day()) if self.from_date.date().isValid() else None
        end = _date(td.year(), td.month(), td.day()) if self.to_date.date().isValid() else None
        rows = list_invoices_between(start, end, qs, limit=1000)
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            # Number
            it_num = QTableWidgetItem(str(row.get("number") or ""))
            it_num.setData(Qt.UserRole, int(row.get("id") or 0))
            self.table.setItem(r, 0, it_num)
            # Date
            d = row.get("date")
            d_text = d.strftime("%d-%m-%Y") if isinstance(d, _date) else str(d or "")
            self.table.setItem(r, 1, QTableWidgetItem(d_text))
            # Customer + phone
            self.table.setItem(r, 2, QTableWidgetItem(str(row.get("customer_name") or "")))
            self.table.setItem(r, 3, QTableWidgetItem(str(row.get("customer_phone") or "")))
            # Total
            total = row.get("total")
            total_text = f"{float(total):.2f}" if isinstance(total, (int, float)) else (str(total or ""))
            it_total = QTableWidgetItem(total_text)
            it_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 4, it_total)

    def _use_selected(self) -> None:
        inv_id = self._current_invoice_id()
        if not inv_id:
            self.selected_invoice_id = None
            self.reject()
            return
        self.selected_invoice_id = int(inv_id)
        self.accept()

    def _open_pdf(self) -> None:
        inv_id = self._current_invoice_id()
        if not inv_id:
            QMessageBox.information(self, "Open PDF", "Please select an invoice.")
            return
        # Try to open the PDF from default save dir by number
        try:
            num = self.table.item(self.table.currentRow(), 0).text()
            from pathlib import Path
            from app.main import SAVE_DIR
            p = Path(SAVE_DIR) / f"{num}.pdf"
            if p.exists():
                from app.printing.print_windows import open_file
                if not open_file(str(p)):
                    QMessageBox.information(self, "Open PDF", f"File saved at: {p}")
            else:
                QMessageBox.information(self, "Open PDF", "PDF not found in default save folder.")
        except Exception as e:
            QMessageBox.warning(self, "Open PDF", f"Could not open PDF.\n\nDetails: {e}")

    def _delete_selected(self) -> None:
        inv_id = self._current_invoice_id()
        if not inv_id:
            QMessageBox.information(self, "Delete", "Please select an invoice to delete.")
            return
        row = self.table.currentRow()
        inv_number = self.table.item(row, 0).text() if row >= 0 else str(inv_id)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete invoice '{inv_number}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            n = delete_invoice(int(inv_id))
            if n == 1:
                QMessageBox.information(self, "Deleted", f"Invoice '{inv_number}' deleted.")
                self._do_search()
            else:
                QMessageBox.information(self, "Delete", "Invoice not found.")
        except Exception as e:
            QMessageBox.warning(self, "Delete Failed", f"Could not delete invoice.\n\nDetails: {e}")
