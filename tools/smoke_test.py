import sqlite3
from datetime import date
from pathlib import Path
import sys
import os

# Ensure project root is on sys.path when running this script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import select

from app.data.db import create_db_and_tables, get_session
from app.data.repo import get_or_create_customer, create_invoice
from app.data.models import Invoice


def main() -> None:
    # Ensure DB schema is up-to-date and tables exist
    create_db_and_tables()

    # Create or fetch a customer for testing
    customer = get_or_create_customer("SmokeTest Customer", phone="9999999999", address="Test Addr")

    # Construct a unique invoice number for today
    base = "SMK-" + date.today().strftime("%Y%m%d")
    with get_session() as s:
        existing = s.exec(select(Invoice).where(Invoice.number.like(f"{base}%"))).all()
        suffix = len(existing) + 1
    inv_no = f"{base}-{suffix}"

    # Create a simple invoice with two items
    inv = create_invoice({
        'number': inv_no,
        'date': date.today(),
        'customer_id': customer.id,
        'notes': 'smoke test',
        'items': [
            {'description': 'A', 'qty': 2, 'rate': 50},
            {'description': 'B', 'qty': 1, 'rate': 25},
        ]
    })

    print("CREATED:", inv.number, inv.total)

    # Verify the invoice table columns (name, notnull)
    conn = sqlite3.connect('kmc.db')
    try:
        cols = conn.execute("PRAGMA table_info('invoice')").fetchall()
        print("INVOICE COLUMNS:", [(c[1], c[3]) for c in cols])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
