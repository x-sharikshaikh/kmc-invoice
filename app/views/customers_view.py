from __future__ import annotations

from typing import List

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem

from app.data.repo import search_customers


class CustomersView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self)
        f = QHBoxLayout()
        f.addWidget(QLabel("Search"))
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("name, phone, address")
        self.btn_clear = QPushButton("Clear")
        self.btn_refresh = QPushButton("Refresh")
        f.addWidget(self.search_edit)
        f.addWidget(self.btn_clear)
        f.addWidget(self.btn_refresh)
        f.addStretch(1)
        v.addLayout(f)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Phone", "Address"])
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        v.addWidget(self.table, 1)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_refresh.clicked.connect(self.refresh)
        self.search_edit.textChanged.connect(lambda _t: self.refresh())
        self._data: List[dict] = []
        self.refresh()

    def _clear(self) -> None:
        self.search_edit.clear()
        self.refresh()

    def refresh(self) -> None:
        q = self.search_edit.text().strip()
        self._data = search_customers(q, 200)
        self.table.setRowCount(len(self._data))
        for r, c in enumerate(self._data):
            self.table.setItem(r, 0, QTableWidgetItem(c.name or ""))
            self.table.setItem(r, 1, QTableWidgetItem(c.phone or ""))
            self.table.setItem(r, 2, QTableWidgetItem(c.address or ""))
        self.table.resizeColumnsToContents()
