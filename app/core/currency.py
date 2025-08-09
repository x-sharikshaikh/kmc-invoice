from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional


def round_money(x: float) -> float:
	"""Round to 2 decimals using banker's rounding (round-half-to-even)."""
	d = Decimal(str(x))  # use str to avoid binary float artifacts
	q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
	return float(q)


def fmt_money(x: float, width: Optional[int] = None) -> str:
	"""
	Format monetary value with two decimals. If width is provided, return a right-aligned string.

	Note: width is optional for convenience when aligning tables in UIs or reports.
	"""
	s = f"{round_money(x):.2f}"
	return s.rjust(width) if isinstance(width, int) and width > 0 else s

