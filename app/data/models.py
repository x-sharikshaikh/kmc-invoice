from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import event


class Customer(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str
	phone: Optional[str] = None
	address: Optional[str] = None

	invoices: List["Invoice"] = Relationship(back_populates="customer")


class Invoice(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	number: str = Field(
		index=True,
		sa_column_kwargs={"unique": True},
	)
	date: date
	customer_id: int = Field(foreign_key="customer.id", index=True)
	subtotal: float = 0.0
	tax: float = 0.0
	total: float = 0.0
	notes: Optional[str] = None

	customer: Optional[Customer] = Relationship(back_populates="invoices")
	items: List["Item"] = Relationship(back_populates="invoice")


class Item(SQLModel, table=True):
	id: Optional[int] = Field(default=None, primary_key=True)
	invoice_id: int = Field(foreign_key="invoice.id", index=True)
	description: str
	qty: float = 0.0
	rate: float = 0.0
	# Stored amount = qty * rate (computed on insert/update)
	amount: float = 0.0

	invoice: Optional[Invoice] = Relationship(back_populates="items")


@event.listens_for(Item, "before_insert")
@event.listens_for(Item, "before_update")
def _compute_item_amount(mapper, connection, target: Item):  # type: ignore[no-redef]
	try:
		q = float(target.qty or 0)
		r = float(target.rate or 0)
		target.amount = q * r
	except Exception:
		target.amount = 0.0

