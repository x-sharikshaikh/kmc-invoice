from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import date as _date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QMessageBox,
)

from app.data.repo import list_invoices_full


class DraftsDialog(QDialog):
    """List saved invoices ("drafts") with basic search and selection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Saved Drafts")
        self.resize(700, 420)
        self.setModal(True)

        root = QVBoxLayout(self)

        # Search row
        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search number or customer…")
        self.btn_search = QPushButton("Search")
        self.btn_use = QPushButton("Use Selected")
        self.btn_delete = QPushButton("Delete")
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.search_edit, 1)
        top.addWidget(self.btn_search)
        top.addStretch(1)
        top.addWidget(self.btn_use)
        top.addWidget(self.btn_delete)
        root.addLayout(top)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Number", "Date", "Customer", "Total"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        # Wire
        self.btn_search.clicked.connect(self._do_search)
        self.search_edit.returnPressed.connect(self._do_search)
        self.btn_use.clicked.connect(self._use_selected)
        self.table.itemDoubleClicked.connect(lambda _it: self._use_selected())
        self.btn_delete.clicked.connect(self._delete_selected)

        # State
        self.selected_invoice_id = None

        # Initial load
        self._do_search()

    def _do_search(self) -> None:
        q = self.search_edit.text().strip()
        rows = list_invoices_full(q, limit=300)
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
            if isinstance(d, _date):
                d_text = d.strftime("%d-%m-%Y")
            else:
                d_text = str(d or "")
            self.table.setItem(r, 1, QTableWidgetItem(d_text))
            # Customer
            self.table.setItem(r, 2, QTableWidgetItem(str(row.get("customer_name") or "")))
            # Total
            total = row.get("total")
            total_text = f"{float(total):.2f}" if isinstance(total, (int, float)) else (str(total or ""))
            it_total = QTableWidgetItem(total_text)
            it_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 3, it_total)

    def _current_invoice_id(self) -> Optional[int]:
        r = self.table.currentRow()
        if r < 0:
            return None
        it = self.table.item(r, 0)
        try:
            return int(it.data(Qt.UserRole)) if it is not None else None
        except Exception:
            return None

    def _use_selected(self) -> None:
        inv_id = self._current_invoice_id()
        if not inv_id:
            self.selected_invoice_id = None
            self.reject()
            return
        self.selected_invoice_id = int(inv_id)
        self.accept()

    def _delete_selected(self) -> None:
        from app.data.repo import delete_invoice
        inv_id = self._current_invoice_id()
        if not inv_id:
            QMessageBox.information(self, "Delete", "Please select a draft to delete.")
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
