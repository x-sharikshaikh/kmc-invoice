from __future__ import annotations

from typing import List, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QScrollArea,
    QPushButton,
    QFrame,
    QAbstractSpinBox,
)

from app.core.currency import round_money, fmt_money


class LineItemRow(QWidget):
    """One editable line item row.

    Emits:
      - subtotalChanged(float): the computed amount for this row after any change
      - removed(QWidget): when the row requests to be removed
    """

    subtotalChanged = Signal(float)
    removed = Signal(QWidget)

    def __init__(self, row_number: int, description: str = "", qty: float = 0.0, rate: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.row_number = row_number

        # Base row layout
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        # Sl. number
        self.lbl_sl = QLabel(str(row_number))
        self.lbl_sl.setFixedWidth(24)
        self.lbl_sl.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.lbl_sl)

        # Description
        self.desc_edit = QLineEdit(description)
        self.desc_edit.setPlaceholderText("Description")
        self.layout.addWidget(self.desc_edit, 1)
        # Ensure description expands
        self.layout.setStretchFactor(self.desc_edit, 1)

        # Qty
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setDecimals(3)
        self.qty_spin.setMinimum(0.0)            # allow 0 quantity
        self.qty_spin.setMaximum(1_000_000_000)  # allow thousands and beyond
        self.qty_spin.setSingleStep(1.0)
        self.qty_spin.setValue(qty)
        self.qty_spin.setAlignment(Qt.AlignRight)
        self.qty_spin.setFixedWidth(110)
        # Hide up/down spinner arrows for a cleaner look
        try:
            self.qty_spin.setButtonSymbols(getattr(QAbstractSpinBox, 'NoButtons', QAbstractSpinBox.ButtonSymbols.NoButtons))
        except Exception:
            pass
        self.layout.addWidget(self.qty_spin)
        # Rate
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setDecimals(2)
        self.rate_spin.setMinimum(0.00)
        self.rate_spin.setMaximum(1_000_000_000)  # allow lakhs and beyond
        self.rate_spin.setSingleStep(1.0)
        self.rate_spin.setValue(rate)
        self.rate_spin.setAlignment(Qt.AlignRight)
        self.rate_spin.setFixedWidth(120)
        # Hide up/down spinner arrows for a cleaner look
        try:
            self.rate_spin.setButtonSymbols(getattr(QAbstractSpinBox, 'NoButtons', QAbstractSpinBox.ButtonSymbols.NoButtons))
        except Exception:
            pass
        self.layout.addWidget(self.rate_spin)

        # Amount (right-aligned, fixed min width)
        self.amount_lbl = QLabel(fmt_money(qty * rate))
        self.amount_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.amount_lbl.setFixedWidth(140)
        self.layout.addWidget(self.amount_lbl)

        # Remove button at end
        self.remove_btn = QPushButton("X")
        self.remove_btn.setFixedWidth(28)
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self))
        self.layout.addWidget(self.remove_btn)

        # Recalculate on change
        self.qty_spin.valueChanged.connect(self._recalc)
        self.rate_spin.valueChanged.connect(self._recalc)

        # Wrap layout inside CardRow frame
        frame = QFrame(self)
        frame.setObjectName("CardRow")
        v = QVBoxLayout(frame)
        v.setContentsMargins(0, 0, 0, 0)
        v.addLayout(self.layout)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

    def _recalc(self) -> None:
        amt = round_money(self.qty_spin.value() * self.rate_spin.value())
        self.amount_lbl.setText(fmt_money(amt))
        self.subtotalChanged.emit(float(amt))

    def get_data(self) -> Dict[str, float | str]:
        return {
            "description": self.desc_edit.text().strip(),
            "qty": float(self.qty_spin.value()),
            "rate": float(self.rate_spin.value()),
            "amount": float(self.qty_spin.value() * self.rate_spin.value()),
        }


class LineItemsWidget(QWidget):
    """A scrollable set of LineItemRow widgets with a simple header.

    Emits:
      - totalsChanged(float): subtotal across all rows
    """

    totalsChanged = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(QLabel("Sl."), 0)
        header.addWidget(QLabel("Description"), 1)
        header.addWidget(QLabel("Qty"), 0)
        header.addWidget(QLabel("Rate"), 0)
        header.addWidget(QLabel("Amount"), 0)
        header.addSpacing(28)  # remove button column
        root.addLayout(header)

        # Scroll area for rows
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.rows_container = QWidget()
        self.vbox = QVBoxLayout(self.rows_container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(6)
        self.scroll.setWidget(self.rows_container)
        root.addWidget(self.scroll)

        # First row
        self.add_row()

    def add_row(self, description: str = "", qty: float = 0.0, rate: float = 0.0) -> None:
        n = self.vbox.count() + 1
        row = LineItemRow(n, description, qty, rate)
        row.subtotalChanged.connect(self._on_subtotal_change)
        row.removed.connect(self.remove_row)
        self.vbox.addWidget(row)
        self._reindex()
        self._emit_totals()

    def remove_row(self, row_widget: QWidget) -> None:
        self.vbox.removeWidget(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()
        self._reindex()
        self._emit_totals()

    def _reindex(self) -> None:
        for i in range(self.vbox.count()):
            w = self.vbox.itemAt(i).widget()
            if hasattr(w, "lbl_sl"):
                w.lbl_sl.setText(str(i + 1))

    def _emit_totals(self) -> None:
        subtotal = 0.0
        for i in range(self.vbox.count()):
            w = self.vbox.itemAt(i).widget()
            if hasattr(w, "get_data"):
                subtotal += float(w.get_data()["amount"])  # type: ignore[index]
        self.totalsChanged.emit(float(subtotal))

    def _on_subtotal_change(self, *_args) -> None:
        self._emit_totals()

    def get_items(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for i in range(self.vbox.count()):
            w = self.vbox.itemAt(i).widget()
            if hasattr(w, "get_data"):
                items.append(w.get_data())
        return items
