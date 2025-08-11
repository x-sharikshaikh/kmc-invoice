from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QLabel,
    QFileDialog,
    QMessageBox,
)

from app.data.repo import (
    search_customers,
    export_customers_csv,
    import_customers_csv,
    delete_customer,
    invoices_count_for_customer,
)


class CustomersDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Customers")
        self.setModal(True)
        self.resize(640, 400)

        root = QVBoxLayout(self)

        # Search bar
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search name, phone, or address…")
        self.btn_search = QPushButton("Search")
        self.btn_export = QPushButton("Export CSV")
        self.btn_import = QPushButton("Import CSV")
        self.btn_use = QPushButton("Use selected")
        self.btn_delete = QPushButton("Delete")
        search_row.addWidget(QLabel("Search:"))
        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.btn_search)
        search_row.addWidget(self.btn_export)
        search_row.addWidget(self.btn_import)
        search_row.addWidget(self.btn_use)
        search_row.addWidget(self.btn_delete)
        root.addLayout(search_row)

        # Results table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Phone", "Address"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        root.addWidget(self.table, 1)

        # Wire
        self.btn_search.clicked.connect(self._do_search)
        self.search_edit.returnPressed.connect(self._do_search)
        self.btn_use.clicked.connect(self._use_selected)
        self.btn_export.clicked.connect(self._export_csv)
        self.btn_import.clicked.connect(self._import_csv)
        self.btn_delete.clicked.connect(self._delete_selected)

        # Initial load
        self._do_search()

        # Holder for chosen customer
        self.selected = None

    def _current_selected_customer(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        item = self.table.item(r, 0)
        return item.data(Qt.UserRole) if item else None

    def _do_search(self) -> None:
        q = self.search_edit.text().strip()
        results = search_customers(q)
        self.table.setRowCount(0)
        for cust in results:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(cust.name or ""))
            self.table.setItem(r, 1, QTableWidgetItem(cust.phone or ""))
            self.table.setItem(r, 2, QTableWidgetItem(cust.address or ""))
            # stash object on row via Qt.UserRole on first column
            self.table.item(r, 0).setData(Qt.UserRole, cust)

    def _use_selected(self) -> None:
        cust = self._current_selected_customer()
        if not cust:
            self.selected = None
            self.reject()
            return
        self.selected = cust
        self.accept()

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Customers",
            str(Path.home() / "customers.csv"),
            "CSV (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        try:
            n = export_customers_csv(path)
            QMessageBox.information(self, "Export Customers", f"Exported {n} customers.")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not export:\n{e}")

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Customers",
            str(Path.home()),
            "CSV (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        try:
            n = import_customers_csv(path)
            QMessageBox.information(self, "Import Customers", f"Imported {n} customers.")
            self._do_search()
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Could not import:\n{e}")

    def _delete_selected(self) -> None:
        cust = self._current_selected_customer()
        if not cust:
            QMessageBox.information(self, "Delete Customer", "Please select a customer to delete.")
            return
        name = cust.name or "(unnamed)"
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete customer '{name}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            n = delete_customer(int(cust.id))  # type: ignore[arg-type]
            if n == 1:
                QMessageBox.information(self, "Delete Customer", f"Deleted '{name}'.")
                self._do_search()
            else:
                QMessageBox.information(self, "Delete Customer", "Customer not found.")
        except ValueError as e:
            # Offer force delete when invoices exist
            msg = str(e)
            count = invoices_count_for_customer(int(cust.id))  # type: ignore[arg-type]
            force_reply = QMessageBox.question(
                self,
                "Cannot Delete",
                f"{msg}\n\nDelete anyway? This will permanently delete {count} invoice(s) and their items.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if force_reply == QMessageBox.Yes:
                try:
                    n = delete_customer(int(cust.id), force=True)  # type: ignore[arg-type]
                    if n == 1:
                        QMessageBox.information(self, "Force Delete", f"Deleted '{name}' and {count} invoice(s).")
                        self._do_search()
                    else:
                        QMessageBox.information(self, "Delete Customer", "Customer not found.")
                except Exception as e2:
                    QMessageBox.warning(self, "Delete Failed", f"Could not delete:\n{e2}")
        except Exception as e:
            QMessageBox.warning(self, "Delete Failed", f"Could not delete:\n{e}")
