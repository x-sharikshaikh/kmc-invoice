from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.data.db import session_scope, get_session, create_db_and_tables
from app.data.models import Customer, Invoice, Item


def get_or_create_customer(name: str, phone: Optional[str] = None, address: Optional[str] = None) -> Customer:
	"""Fetch an existing customer by name/phone (case-insensitive), or create one."""
	normalized_name = (name or "").strip()
	if not normalized_name:
		raise ValueError("Customer name is required")

	with session_scope() as s:
		stmt = select(Customer).where(func.lower(Customer.name) == normalized_name.lower())
		if phone:
			stmt = stmt.where((Customer.phone == phone))
		existing = s.exec(stmt).first()
		if existing:
			return existing

		customer = Customer(name=normalized_name, phone=phone, address=address)
		s.add(customer)
		s.flush()
		s.refresh(customer)
		return customer


def create_invoice(invoice_dto: Dict[str, Any]) -> Invoice:
	"""
	Create an invoice and its items.

	invoice_dto structure:
	  {
		'number': str,  # required (must be unique)
		'date': datetime.date,  # required
		'customer_id': int,  # required (use get_or_create_customer separately if needed)
		'notes': str | None,  # optional
		'tax': float | None,  # optional; defaults to 0.0
		'items': [
		   {'description': str, 'qty': float, 'rate': float}, ...
		]  # required, can be empty
	  }
	Subtotal and total are computed: subtotal=sum(qty*rate); total=subtotal+tax.
	"""
	number = invoice_dto.get("number")
	inv_date: date = invoice_dto.get("date")
	customer_id: Optional[int] = invoice_dto.get("customer_id")
	notes: Optional[str] = invoice_dto.get("notes")
	tax_val: float = float(invoice_dto.get("tax", 0.0) or 0.0)
	items_dto: Iterable[Dict[str, Any]] = invoice_dto.get("items", []) or []

	if not (number and isinstance(inv_date, date) and isinstance(customer_id, int)):
		raise ValueError("Missing required fields: number, date, customer_id")

	# Basic duplicate check for invoice number
	with session_scope() as s:
		dup = s.exec(select(Invoice).where(Invoice.number == number)).first()
		if dup:
			raise ValueError(f"Invoice number already exists: {number}")

		# Compute subtotal from items
		subtotal_val = 0.0
		for item in items_dto:
			q = float(item.get("qty", 0) or 0)
			r = float(item.get("rate", 0) or 0)
			subtotal_val += q * r
		total_val = subtotal_val + tax_val

		inv = Invoice(
			number=str(number),
			date=inv_date,
			customer_id=customer_id,
			subtotal=float(subtotal_val),
			tax=float(tax_val),
			total=float(total_val),
			notes=notes,
		)
		s.add(inv)
		s.flush()
		s.refresh(inv)

		# Add items
		for item in items_dto:
			it = Item(
				invoice_id=inv.id,  # type: ignore[arg-type]
				description=str(item.get("description", "")),
				qty=float(item.get("qty", 0) or 0),
				rate=float(item.get("rate", 0) or 0),
			)
			s.add(it)

		s.flush()
		# Refresh items relationship
		s.refresh(inv)
		return inv


def list_invoices(limit: Optional[int] = None) -> List[Invoice]:
	"""Return invoices ordered by date DESC, id DESC, with customer eagerly loaded."""
	with get_session() as s:
		stmt = (
			select(Invoice)
			.options(selectinload(Invoice.customer))
			.order_by(Invoice.date.desc(), Invoice.id.desc())
		)
		if isinstance(limit, int) and limit > 0:
			stmt = stmt.limit(limit)
		return list(s.exec(stmt).all())


def get_invoice_by_number(number: str) -> Optional[Invoice]:
	"""Fetch a single invoice by its unique number, including items and customer."""
	with get_session() as s:
		stmt = (
			select(Invoice)
			.where(Invoice.number == number)
			.options(
				selectinload(Invoice.customer),
				selectinload(Invoice.items),
			)
		)
		return s.exec(stmt).first()

