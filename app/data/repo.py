from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Optional
import csv
from pathlib import Path

from sqlmodel import Session, select
from sqlalchemy import func, delete
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


def list_invoices_full(query: str = "", limit: int = 200) -> List[Dict[str, Any]]:
	"""List recent invoices with customer and totals for UI listing.

	Returns list of dicts: {id, number, date, customer_name, customer_phone, total}
	Applies case-insensitive filtering on invoice number and customer name when query provided.
	"""
	q = (query or "").strip().lower()
	with get_session() as s:
		# Select explicit columns for robust cross-version compatibility
		stmt = (
			select(
				Invoice.id,
				Invoice.number,
				Invoice.date,
				Invoice.total,
				Customer.name.label("customer_name"),
				Customer.phone.label("customer_phone"),
			)
			.select_from(Invoice)
			.join(Customer, Customer.id == Invoice.customer_id, isouter=True)
			.order_by(Invoice.date.desc(), Invoice.id.desc())
		)
		if q:
			like = f"%{q}%"
			stmt = stmt.where(
				(func.lower(Invoice.number).like(like))
				| (func.lower(Customer.name).like(like))
			)
		if limit and isinstance(limit, int):
			stmt = stmt.limit(limit)
		rows = list(s.exec(stmt).all())
		out: List[Dict[str, Any]] = []
		for r in rows:
			try:
				inv_id, number, d, total, cust_name, cust_phone = r
			except Exception:
				# Fallback if row is a dict-like
				inv_id = r[0]; number = r[1]; d = r[2]; total = r[3]; cust_name = r[4] if len(r) > 4 else None; cust_phone = r[5] if len(r) > 5 else None
			out.append({
				"id": int(inv_id),
				"number": str(number),
				"date": d,
				"customer_name": cust_name,
				"customer_phone": cust_phone,
				"total": float(total or 0.0),
			})
		return out


def get_invoice_with_items(invoice_id: int) -> Optional[Dict[str, Any]]:
	"""Fetch a single invoice with its customer and items, as plain dicts for the UI.

	Returns None if not found, else a dict with keys:
	  invoice: {id, number, date, total, notes}
	  customer: {id, name, phone, address}
	  items: [{description, qty, rate, amount}]
	"""
	with get_session() as s:
		inv = s.get(Invoice, invoice_id)
		if not inv:
			return None
		cust = s.get(Customer, getattr(inv, "customer_id", None)) if getattr(inv, "customer_id", None) is not None else None
		item_rows = s.exec(select(Item).where(Item.invoice_id == inv.id).order_by(Item.id.asc())).all()
		items = [
			{
				"description": getattr(it, "description", ""),
				"qty": float(getattr(it, "qty", 0.0) or 0.0),
				"rate": float(getattr(it, "rate", 0.0) or 0.0),
				"amount": float(getattr(it, "amount", (getattr(it, "qty", 0.0) or 0.0) * (getattr(it, "rate", 0.0) or 0.0))),
			}
			for it in (item_rows or [])
		]
		return {
			"invoice": {
				"id": inv.id,
				"number": inv.number,
				"date": inv.date,
				"total": float(getattr(inv, "total", 0.0) or 0.0),
				"notes": getattr(inv, "notes", None),
			},
			"customer": {
				"id": getattr(cust, "id", None) if cust else None,
				"name": getattr(cust, "name", None) if cust else None,
				"phone": getattr(cust, "phone", None) if cust else None,
				"address": getattr(cust, "address", None) if cust else None,
			},
			"items": items,
		}


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


def invoices_count_for_customer(customer_id: int) -> int:
	"""Return number of invoices associated with a customer."""
	with get_session() as s:
		inv_count = s.exec(
			select(func.count(Invoice.id)).where(Invoice.customer_id == customer_id)
		).one()
		try:
			return int(inv_count)
		except Exception:
			return int(inv_count[0]) if isinstance(inv_count, (list, tuple)) else 0


def delete_customer(customer_id: int, *, force: bool = False) -> int:
	"""Delete a customer by id.

	Behavior:
	- When force is False (default): only delete if the customer has no invoices; otherwise raise ValueError.
	- When force is True: delete the customer and ALL their invoices and items in a single transaction.

	Returns 1 if deleted, 0 if not found.
	"""
	with session_scope() as s:
		cust = s.get(Customer, customer_id)
		if not cust:
			return 0

		# Collect invoice ids for this customer (robust across SQLAlchemy/SQLModel versions)
		_res = s.exec(select(Invoice.id).where(Invoice.customer_id == customer_id))
		try:
			# Newer SQLAlchemy Result supports .scalars()
			inv_ids = list(_res.scalars().all())  # type: ignore[attr-defined]
		except Exception:
			# Older/other forms: .all() may already be a list of ints or single-col tuples
			try:
				rows = _res.all()  # type: ignore[attr-defined]
			except Exception:
				rows = list(_res)
			inv_ids = [
				(int(r[0]) if isinstance(r, (list, tuple)) else int(r))
				for r in rows
			]

		if inv_ids and not force:
			raise ValueError(f"Cannot delete: customer has {len(inv_ids)} invoice(s).")

		# If forcing, remove dependent records first to keep integrity on all SQLite versions
		if inv_ids:
			s.exec(delete(Item).where(Item.invoice_id.in_(inv_ids)))
			s.exec(delete(Invoice).where(Invoice.id.in_(inv_ids)))

		s.delete(cust)
		s.flush()
		return 1


def delete_invoice(invoice_id: int) -> int:
	"""Delete a single invoice and all of its items. Returns 1 if deleted, 0 if not found."""
	with session_scope() as s:
		inv = s.get(Invoice, invoice_id)
		if not inv:
			return 0
		# Remove dependent items first for compatibility across SQLite versions
		s.exec(delete(Item).where(Item.invoice_id == invoice_id))
		s.delete(inv)
		s.flush()
		return 1

