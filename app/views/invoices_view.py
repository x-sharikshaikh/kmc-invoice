from __future__ import annotations

from datetime import date
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from app.data.repo import list_invoices_between


class InvoicesView(QWidget):
    invoiceActivated = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self)

        # Filters
        f = QHBoxLayout()
        f.addWidget(QLabel("Search"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("invoice number or customer name")
        f.addWidget(self.search_edit)
        f.addSpacing(12)
        f.addWidget(QLabel("From"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        f.addWidget(self.from_date)
        f.addWidget(QLabel("To"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        f.addWidget(self.to_date)
        self.btn_clear = QPushButton("Clear")
        self.btn_refresh = QPushButton("Refresh")
        f.addWidget(self.btn_clear)
        f.addWidget(self.btn_refresh)
        f.addStretch(1)
        v.addLayout(f)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Number", "Date", "Customer", "Phone", "Total"])
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        v.addWidget(self.table, 1)
        self.table.itemDoubleClicked.connect(lambda _it: self._emit_current())

        # Events
        self.btn_clear.clicked.connect(self._clear_filters)
        self.btn_refresh.clicked.connect(self.refresh)
        self.search_edit.textChanged.connect(lambda _t: self.refresh())

        # Defaults
        self._data = []
        self.refresh()

    def _clear_filters(self) -> None:
        self.search_edit.clear()
        self.from_date.clear()
        self.to_date.clear()
        self.refresh()

    def refresh(self) -> None:
        sd = self.from_date.date().toPython() if self.from_date.date().isValid() else None
        ed = self.to_date.date().toPython() if self.to_date.date().isValid() else None
        q = self.search_edit.text().strip()
        self._data = list_invoices_between(sd, ed, q, 500)
        self._render()

    def _render(self) -> None:
        self.table.setRowCount(len(self._data))
        for r, row in enumerate(self._data):
            self.table.setItem(r, 0, QTableWidgetItem(str(row.get("number", ""))))
            d = row.get("date")
            dstr = d.strftime("%d-%m-%Y") if hasattr(d, "strftime") else str(d)
            self.table.setItem(r, 1, QTableWidgetItem(dstr))
            self.table.setItem(r, 2, QTableWidgetItem(str(row.get("customer_name", ""))))
            self.table.setItem(r, 3, QTableWidgetItem(str(row.get("customer_phone", ""))))
            self.table.setItem(r, 4, QTableWidgetItem(f"{row.get('total', 0.0):.2f}"))
        self.table.resizeColumnsToContents()

    def current_invoice_id(self) -> Optional[int]:
        r = self.table.currentRow()
        if r < 0 or r >= len(self._data):
            return None
        try:
            return int(self._data[r].get("id"))
        except Exception:
            return None

    def _emit_current(self) -> None:
        cid = self.current_invoice_id()
        if cid is not None:
            self.invoiceActivated.emit(int(cid))
