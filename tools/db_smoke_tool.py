from __future__ import annotations

from datetime import date
import time

from app.data.db import create_db_and_tables
from app.data.repo import get_or_create_customer, create_invoice, list_invoices


def main() -> None:
    create_db_and_tables()
    c = get_or_create_customer("Test User", phone="123", address="Somewhere")
    print("Customer:", c.id, c.name)
    num = f"TEST-{int(time.time())}"
    inv = create_invoice({
        'number': num,
        'date': date.today(),
        'customer_id': c.id,
        'notes': 'hello',
        'items': [
            {'description': 'Widget', 'qty': 2, 'rate': 10},
            {'description': 'Service', 'qty': 1, 'rate': 5},
        ],
    })
    print("Invoice:", inv.id, inv.number, inv.total)
    print("Invoices count:", len(list_invoices()))


if __name__ == "__main__":
    main()
