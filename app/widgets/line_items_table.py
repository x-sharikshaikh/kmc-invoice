from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from app.core.currency import fmt_money, round_money


class LineItemsTable(QTableWidget):
	"""Invoice line items table with auto numbering and totals signal."""

	totalsChanged = Signal(float)  # emits subtotal

	COL_SL = 0
	COL_DESC = 1
	COL_QTY = 2
	COL_RATE = 3
	COL_AMT = 4

	def __init__(self, parent=None) -> None:
		super().__init__(0, 5, parent)
		self.setHorizontalHeaderLabels(["Sl.", "Description", "Qty", "Rate", "Amount"])
		self.horizontalHeader().setStretchLastSection(True)
		self.verticalHeader().setVisible(False)
		self.setAlternatingRowColors(True)
		self.itemChanged.connect(self._on_item_changed)

	def add_row(self, description: str = "", qty: float = 0.0, rate: float = 0.0) -> None:
		r = self.rowCount()
		self.insertRow(r)
		# Sl. (read-only)
		sl = QTableWidgetItem(str(r + 1))
		sl.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
		self.setItem(r, self.COL_SL, sl)
		# Description
		self.setItem(r, self.COL_DESC, QTableWidgetItem(description))
		# Qty
		qty_item = QTableWidgetItem(self._format_qty(qty))
		qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
		self.setItem(r, self.COL_QTY, qty_item)
		# Rate
		rate_item = QTableWidgetItem(fmt_money(rate))
		rate_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
		self.setItem(r, self.COL_RATE, rate_item)
		# Amount (read-only)
		amt_val = round_money((qty or 0.0) * (rate or 0.0))
		amt_item = QTableWidgetItem(fmt_money(amt_val))
		amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
		amt_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
		self.setItem(r, self.COL_AMT, amt_item)
		# Emit new subtotal
		self._emit_totals()

	def remove_selected_rows(self) -> None:
		rows = sorted({idx.row() for idx in self.selectedIndexes()}, reverse=True)
		if not rows:
			return
		for r in rows:
			self.removeRow(r)
		self._renumber()
		self._emit_totals()

	def _renumber(self) -> None:
		for i in range(self.rowCount()):
			it = self.item(i, self.COL_SL)
			if it is None:
				it = QTableWidgetItem(str(i + 1))
				it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
				self.setItem(i, self.COL_SL, it)
			else:
				it.setText(str(i + 1))

	def _on_item_changed(self, item: QTableWidgetItem) -> None:
		c = item.column()
		r = item.row()
		if c in (self.COL_QTY, self.COL_RATE, self.COL_DESC):
			# Validate and normalize qty/rate
			qty = self._parse_float(self.item(r, self.COL_QTY))
			rate = self._parse_float(self.item(r, self.COL_RATE))
			# Normalize display
			self.blockSignals(True)
			if self.item(r, self.COL_QTY):
				self.item(r, self.COL_QTY).setText(self._format_qty(qty))
				self.item(r, self.COL_QTY).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
			if self.item(r, self.COL_RATE):
				self.item(r, self.COL_RATE).setText(fmt_money(rate))
				self.item(r, self.COL_RATE).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
			# Amount
			amt_val = round_money(qty * rate)
			amt_item = self.item(r, self.COL_AMT)
			if amt_item is None:
				amt_item = QTableWidgetItem(fmt_money(amt_val))
				amt_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
				self.setItem(r, self.COL_AMT, amt_item)
			else:
				amt_item.setText(fmt_money(amt_val))
			amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
			self.blockSignals(False)
			self._emit_totals()

	def _parse_float(self, item: Optional[QTableWidgetItem]) -> float:
		try:
			return float(item.text()) if item and item.text() else 0.0
		except Exception:
			return 0.0

	def _format_qty(self, x: float) -> str:
		# Show up to 3 decimals for quantity without trailing zeros, but keep numeric
		s = f"{x:.3f}".rstrip("0").rstrip(".")
		return s if s else "0"

	def _emit_totals(self) -> None:
		subtotal = 0.0
		for r in range(self.rowCount()):
			subtotal += self._parse_float(self.item(r, self.COL_AMT))
		self.totalsChanged.emit(round_money(subtotal))

