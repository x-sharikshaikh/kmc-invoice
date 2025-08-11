from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Optional
import csv
from pathlib import Path

from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.data.db import session_scope, get_session, create_db_and_tables
from app.data.models import Customer, Invoice, Item
from app.core.currency import round_money


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
		# Ensure PK is populated before leaving the session
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
		'items': [
		   {'description': str, 'qty': float, 'rate': float}, ...
		]  # required, can be empty
	  }
	Total is computed as sum(qty*rate).
	"""
	number = invoice_dto.get("number")
	inv_date: date = invoice_dto.get("date")
	customer_id: Optional[int] = invoice_dto.get("customer_id")
	notes: Optional[str] = invoice_dto.get("notes")
	# tax removed; tolerate legacy 'tax' key but ignore its value
	_ = invoice_dto.get("tax", 0.0)
	items_dto: Iterable[Dict[str, Any]] = invoice_dto.get("items", []) or []

	if not (number and isinstance(inv_date, date) and isinstance(customer_id, int)):
		raise ValueError("Missing required fields: number, date, customer_id")

	# Basic duplicate check for invoice number
	with session_scope() as s:
		dup = s.exec(select(Invoice).where(Invoice.number == number)).first()
		if dup:
			raise ValueError(f"Invoice number already exists: {number}")

		# Compute total from items only (no subtotal field persisted)
		total_val = 0.0
		for item in items_dto:
			q = float(item.get("qty", 0) or 0)
			r = float(item.get("rate", 0) or 0)
			total_val += q * r
		total_val = round_money(total_val)

		inv = Invoice(
			number=str(number),
			date=inv_date,
			customer_id=customer_id,
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

	# After commit, the returned instance is detached but not expired (expire_on_commit=False)
	return inv


def list_invoices(limit: Optional[int] = None) -> List[Invoice]:
    """Return invoices ordered by date DESC, id DESC."""
    with get_session() as s:
        stmt = select(Invoice).order_by(Invoice.date.desc(), Invoice.id.desc())
        if isinstance(limit, int) and limit > 0:
            stmt = stmt.limit(limit)
        return list(s.exec(stmt).all())


def get_invoice_by_number(number: str) -> Optional[Invoice]:
    """Fetch a single invoice by its unique number."""
    with get_session() as s:
        stmt = select(Invoice).where(Invoice.number == number)
        return s.exec(stmt).first()


def search_customers(query: str = "", limit: int = 50) -> List[Customer]:
	"""Search customers by name, phone, or address (case-insensitive). Returns up to limit results.

	If query is blank, returns recent customers ordered by name ASC then id DESC.
	"""
	q = (query or "").strip().lower()
	with get_session() as s:
		stmt = select(Customer)
		if q:
			like = f"%{q}%"
			# SQLite is case-insensitive with LIKE for ASCII; ensure lower() comparison for consistency
			stmt = stmt.where(
				(func.lower(Customer.name).like(like))
				| (Customer.phone.like(like))
				| (func.lower(Customer.address).like(like))
			)
		stmt = stmt.order_by(Customer.name.asc(), Customer.id.desc()).limit(int(limit) if limit else 50)
		return list(s.exec(stmt).all())


def export_customers_csv(path: str | Path) -> int:
	"""Export all customers to a CSV file. Returns number of rows written.

	Columns: name,phone,address
	"""
	p = Path(path)
	p.parent.mkdir(parents=True, exist_ok=True)
	count = 0
	with get_session() as s:
		rows = s.exec(select(Customer).order_by(Customer.name.asc(), Customer.id.asc())).all()
		with p.open("w", encoding="utf-8", newline="") as f:
			w = csv.writer(f)
			w.writerow(["name", "phone", "address"])  # header
			for c in rows:
				w.writerow([c.name or "", c.phone or "", c.address or ""]) 
				count += 1
	return count


def import_customers_csv(path: str | Path) -> int:
	"""Import customers from CSV (name,phone,address). Returns number of inserted/updated rows.

	Rules:
	- If a row's name is empty, it's skipped.
	- If a customer with the same name (case-insensitive) exists, update phone/address if provided.
	- Otherwise, create a new customer.
	"""
	p = Path(path)
	if not p.exists():
		return 0
	imported = 0
	with session_scope() as s:
		with p.open("r", encoding="utf-8", newline="") as f:
			r = csv.DictReader(f)
			for row in r:
				name = (row.get("name") or "").strip()
				if not name:
					continue
				phone = (row.get("phone") or "").strip() or None
				address = (row.get("address") or "").strip() or None
				# lookup existing by lower(name)
				existing = s.exec(select(Customer).where(func.lower(Customer.name) == name.lower())).first()
				if existing:
					existing.phone = phone or existing.phone
					existing.address = address or existing.address
				else:
					s.add(Customer(name=name, phone=phone, address=address))
				imported += 1
	return imported

