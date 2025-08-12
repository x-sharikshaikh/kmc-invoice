from __future__ import annotations

from typing import List, Dict, Any

from PySide6.QtCore import Qt, Signal, QLocale
from PySide6.QtGui import QValidator
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

from app.core.currency import round_money, fmt_money, to_decimal, round_money_dec


class BlankZeroDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that shows blank at zero, right-aligned, and avoids reversed input.
    - Shows blank when value == minimum (0.0) using non-empty specialValueText.
    - Forces LTR inside the editor and moves caret to end on focus for natural typing.
    """

    def __init__(self, decimals: int = 2, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDecimals(decimals)
        self.setMinimum(0.0)
        self.setMaximum(1_000_000_000)
        self.setSingleStep(1.0)
        self.setKeyboardTracking(False)
        self.setSpecialValueText(" ")  # non-empty to take effect
        # Use C locale and hide group separators to avoid unexpected formatting while typing
        try:
            self.setLocale(QLocale.c())
        except Exception:
            pass
        try:
            self.setGroupSeparatorShown(False)
        except Exception:
            pass
        # UI polish
        try:
            self.setButtonSymbols(getattr(QAbstractSpinBox, 'NoButtons', QAbstractSpinBox.ButtonSymbols.NoButtons))
        except Exception:
            pass
        # Left align to avoid cursor jumping/reformat issues while typing
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Prefer numeric input on touch/keyboards
        try:
            self.setInputMethodHints(getattr(Qt, 'ImhDigitsOnly', 0) | getattr(Qt, 'ImhPreferNumbers', 0))
        except Exception:
            pass
        # Prevent reversed insertion by forcing LTR on the line edit
        try:
            le = self.lineEdit()
            if le is not None:
                le.setLayoutDirection(Qt.LeftToRight)
        except Exception:
            pass

    def focusInEvent(self, event) -> None:  # type: ignore[override]
        super().focusInEvent(event)
        try:
            le = self.lineEdit()
            if le is not None:
                le.setCursorPosition(len(le.text()))
        except Exception:
            pass

    # Stronger control over parsing/formatting to avoid mid-typing reformat and reversed digits
    def textFromValue(self, value: float) -> str:  # type: ignore[override]
        if value <= self.minimum() + 1e-12:
            # Let specialValueText handle blank-at-zero
            svt = self.specialValueText()
            return svt if svt else ""
        # Fixed-point formatting with set decimals, no locale grouping
        try:
            return f"{value:.{self.decimals()}f}"
        except Exception:
            return str(value)

    def valueFromText(self, text: str) -> float:  # type: ignore[override]
        s = text.strip()
        if not s or s == self.specialValueText().strip():
            return self.minimum()
        # Remove any stray commas/spaces
        s = s.replace(",", "")
        # Normalize unicode digits to ASCII if needed
        try:
            # Basic conversion; invalid input falls back to min
            return max(self.minimum(), min(self.maximum(), float(s)))
        except Exception:
            return self.minimum()

    def validate(self, text: str, pos: int):  # type: ignore[override]
        s = text.strip()
        if not s:
            return (QValidator.Intermediate, text, pos)
        # Allow digits with optional single dot and up to 'decimals' fraction digits
        allowed = "0123456789."
        if any(ch not in allowed for ch in s):
            return (QValidator.Invalid, text, pos)
        if s.count(".") > 1:
            return (QValidator.Invalid, text, pos)
        if "." in s:
            left, right = s.split(".", 1)
            if len(right) > self.decimals():
                return (QValidator.Invalid, text, pos)
            if left == "":
                # ".5" style while typing
                return (QValidator.Intermediate, text, pos)
        # Large integers while typing are okay
        return (QValidator.Acceptable, text, pos)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        # After processing the key, keep caret at end to ensure digits append naturally
        super().keyPressEvent(event)
        try:
            le = self.lineEdit()
            if le is not None:
                le.setCursorPosition(len(le.text()))
        except Exception:
            pass

    def stepBy(self, steps: int) -> None:  # type: ignore[override]
        # Keep default behavior, but ensure we don't re-enable keyboard tracking glitches
        super().stepBy(steps)
        try:
            le = self.lineEdit()
            if le is not None:
                le.setCursorPosition(len(le.text()))
        except Exception:
            pass


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
        self.layout.setStretchFactor(self.desc_edit, 1)

        # Qty
        self.qty_spin = BlankZeroDoubleSpinBox(decimals=2)
        self.qty_spin.setValue(qty)
        self.qty_spin.setFixedWidth(110)
        self.layout.addWidget(self.qty_spin)

        # Rate
        self.rate_spin = BlankZeroDoubleSpinBox(decimals=2)
        self.rate_spin.setValue(rate)
        self.rate_spin.setFixedWidth(120)
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

        # Wrap the row in a CardRow frame
        frame = QFrame(self)
        frame.setObjectName("CardRow")
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addLayout(self.layout)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

    def _recalc(self) -> None:
        amt_dec = round_money_dec(to_decimal(self.qty_spin.value()) * to_decimal(self.rate_spin.value()))
        self.amount_lbl.setText(fmt_money(amt_dec))
        self.subtotalChanged.emit(float(amt_dec))

    def get_data(self) -> Dict[str, float | str]:
        qty = to_decimal(self.qty_spin.value())
        rate = to_decimal(self.rate_spin.value())
        amt = round_money_dec(qty * rate)
        return {
            "description": self.desc_edit.text().strip(),
            "qty": float(qty),
            "rate": float(rate),
            "amount": float(amt),
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
                data = w.get_data()
                if isinstance(data, dict) and data.get("amount") is not None:
                    subtotal += float(data["amount"])  # type: ignore[index]
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
