from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from typing import Optional, Iterable


def to_decimal(x: object) -> Decimal:
	"""Best-effort conversion to Decimal via str to avoid binary float artifacts."""
	try:
		return Decimal(str(x))
	except (InvalidOperation, ValueError, TypeError):
		return Decimal("0")


def round_money(x: float | Decimal) -> float:
	"""Round to 2 decimals using banker's rounding (round-half-to-even) and return float.

	Backward-compatible helper for places expecting float output.
	"""
	d = to_decimal(x)
	q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
	return float(q)


def round_money_dec(x: float | Decimal) -> Decimal:
	"""Round to 2 decimals and return Decimal for high-precision internal math."""
	d = to_decimal(x)
	return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def fmt_money(x: float | Decimal, width: Optional[int] = None) -> str:
	"""
	Format monetary value with two decimals. If width is provided, return a right-aligned string.

	Note: width is optional for convenience when aligning tables in UIs or reports.
	"""
	# Ensure proper rounding then format
	if isinstance(x, Decimal):
		q = round_money_dec(x)
		s = f"{q:.2f}"
	else:
		s = f"{round_money(x):.2f}"
	return s.rjust(width) if isinstance(width, int) and width > 0 else s


def sum_money(values: Iterable[float | Decimal]) -> Decimal:
	"""Accumulate monetary values using Decimal and banker's rounding at the end."""
	total = Decimal("0")
	for v in values:
		total += to_decimal(v)
	return round_money_dec(total)

