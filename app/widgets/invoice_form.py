from __future__ import annotations

from datetime import date as _date
from typing import Any, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QWidget,
	QGroupBox,
	QFormLayout,
	QLineEdit,
	QTextEdit,
	QDateEdit,
	QVBoxLayout,
	QHBoxLayout,
	QLabel,
)

from app.core.currency import fmt_money, round_money
from app.core.settings import load_settings, Settings
from app.widgets.line_items_widget import LineItemsWidget


class InvoiceForm(QWidget):
	"""Widget aggregating Bill To, Invoice Info, Line Items, and Totals.

	Exposes collect_data() -> dict for PDF generation and DB save.
	"""

	totalsChanged = Signal(float)  # re-emitted from table

	def __init__(self, parent=None, settings: Settings | None = None) -> None:
		super().__init__(parent)
		self.settings = settings or load_settings()

		root = QVBoxLayout(self)
		root.setContentsMargins(0, 0, 0, 0)
		root.setSpacing(8)

		# Top groups: Bill To and Invoice Info
		top = QHBoxLayout()
		top.setSpacing(12)

		bill_group = QGroupBox("BILL TO")
		bill_form = QFormLayout(bill_group)
		bill_form.setLabelAlignment(Qt.AlignRight)
		self.name_edit = QLineEdit()
		self.phone_edit = QLineEdit()
		self.addr_edit = QTextEdit()
		self.addr_edit.setFixedHeight(70)
		bill_form.addRow("Name", self.name_edit)
		bill_form.addRow("Phone", self.phone_edit)
		bill_form.addRow("Address", self.addr_edit)

		info_group = QGroupBox("Invoice Info")
		info_form = QFormLayout(info_group)
		info_form.setLabelAlignment(Qt.AlignRight)
		self.inv_number = QLineEdit()
		self.inv_number.setReadOnly(True)
		self.date_edit = QDateEdit()
		self.date_edit.setDisplayFormat("dd-MM-yyyy")
		self.date_edit.setDate(self.date_edit.minimumDate().currentDate())
		info_form.addRow("Number", self.inv_number)
		info_form.addRow("Date", self.date_edit)

		top.addWidget(bill_group, 1)
		top.addWidget(info_group, 1)
		root.addLayout(top)

		# Line items widget (rows-based)
		self.table = LineItemsWidget(self)
		root.addWidget(self.table)

		# Totals area (right aligned)
		totals_row = QHBoxLayout()
		totals_row.addStretch(1)
		totals_box = QVBoxLayout()

		row_sub = QHBoxLayout()
		row_sub.addWidget(QLabel("Subtotal:"))
		self.subtotal_lbl = QLabel("0.00")
		row_sub.addWidget(self.subtotal_lbl, 0, Qt.AlignRight)

		row_tax = QHBoxLayout()
		row_tax.addWidget(QLabel("Tax:"))
		self.tax_lbl = QLabel("0.00")
		row_tax.addWidget(self.tax_lbl, 0, Qt.AlignRight)

		row_total = QHBoxLayout()
		total_label = QLabel("Total:" )
		total_label.setStyleSheet("font-weight: 600; font-size: 14px;")
		self.total_lbl = QLabel("0.00")
		self.total_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
		row_total.addWidget(total_label)
		row_total.addWidget(self.total_lbl, 0, Qt.AlignRight)

		totals_box.addLayout(row_sub)
		totals_box.addLayout(row_tax)
		totals_box.addLayout(row_total)
		totals_row.addLayout(totals_box)
		root.addLayout(totals_row)

		# Connect signals
		self.table.totalsChanged.connect(self._on_subtotal_changed)

		# Start with one row (LineItemsWidget already adds one by default; keep explicit call harmless)
		self.table.add_row()

	# External helpers
	def set_invoice_number(self, number: str) -> None:
		self.inv_number.setText(number)

	def add_row(self, *args, **kwargs) -> None:
		self.table.add_row(*args, **kwargs)

	def remove_selected_rows(self) -> None:
		# Per-row remove buttons exist; keep stub for compatibility or future use
		pass

	def _on_subtotal_changed(self, subtotal: float) -> None:
		tax = round_money(subtotal * float(self.settings.tax_rate))
		total = round_money(subtotal + tax)
		self.subtotal_lbl.setText(fmt_money(subtotal))
		self.tax_lbl.setText(fmt_money(tax))
		self.total_lbl.setText(fmt_money(total))
		self.totalsChanged.emit(subtotal)

	def _collect_items(self) -> List[Dict[str, Any]]:
		# Delegate to the new widget
		return self.table.get_items()

	def collect_data(self) -> Dict[str, Any]:
		"""Collect form data suitable for PDF generation and DB save.

		Returns dict with keys:
		  customer: {name, phone, address}
		  invoice: {number, date (datetime.date), tax_rate}
		  items: [{description, qty, rate, amount}]
		  subtotal: float
		  tax: float
		  total: float
		"""
		number = self.inv_number.text().strip()
		qd = self.date_edit.date()
		inv_date = _date(qd.year(), qd.month(), qd.day())
		items = self._collect_items()
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
				'number': number,
				'date': inv_date,
				'tax_rate': float(self.settings.tax_rate),
			},
			'items': items,
			'subtotal': subtotal,
			'tax': tax,
			'total': total,
		}

