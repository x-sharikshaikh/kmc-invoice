from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import LETTER
from app.pdf.table_layout import build_invoice_table

out = Path("sample_invoice.pdf")
lines = [
    {"sl": "1.", "description": "Electrical inspection and diagnostics", "qty": 1, "rate": 120.00, "amount": 120.00},
    {"sl": "2.", "description": "Wiring repair (per room)", "qty": 2, "rate": 85.50, "amount": 171.00},
    {"sl": "3.", "description": "LED fixture installation", "qty": 3, "rate": 45.00, "amount": 135.00},
    {"sl": "4.", "description": "Breaker replacement", "qty": 1, "rate": 65.75, "amount": 65.75},
    {"sl": "5.", "description": "Safety compliance testing", "qty": 1, "rate": 90.00, "amount": 90.00},
]
total_amt = sum(r["amount"] for r in lines)

doc = SimpleDocTemplate(str(out), pagesize=LETTER, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=54)

story = [build_invoice_table(lines, total=total_amt, content_width=doc.width), Spacer(1, 12)]
doc.build(story)
print(f"Created {out.resolve()}")
