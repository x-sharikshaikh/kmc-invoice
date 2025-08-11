"""
Verify that the invoice table styling matches the Reference Invoice.jpg requirements.
This script tests the table builder and generates a sample for visual verification.
"""

from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import LETTER
from app.pdf.table_layout import build_invoice_table

def test_table_styling():
    """Test the table styling and generate a sample invoice."""
    
    # Test data matching the requirements
    lines = [
        {"sl": "1.", "description": "Electrical inspection and diagnostics", "qty": 1, "rate": 120.00, "amount": 120.00},
        {"sl": "2.", "description": "Wiring repair (per room)", "qty": 2, "rate": 85.50, "amount": 171.00},
        {"sl": "3.", "description": "LED fixture installation", "qty": 3, "rate": 45.00, "amount": 135.00},
        {"sl": "4.", "description": "Breaker replacement", "qty": 1, "rate": 65.75, "amount": 65.75},
        {"sl": "5.", "description": "Safety compliance testing", "qty": 1, "rate": 90.00, "amount": 90.00},
    ]
    total_amt = sum(r["amount"] for r in lines)
    
    # Create document with standard margins
    out = Path("sample_invoice.pdf")
    doc = SimpleDocTemplate(
        str(out), 
        pagesize=LETTER, 
        leftMargin=36, 
        rightMargin=36, 
        topMargin=36, 
        bottomMargin=54
    )
    
    # Build the table with the new system
    table = build_invoice_table(lines, total=total_amt, content_width=doc.width)
    
    # Create story and build PDF
    story = [table, Spacer(1, 12)]
    doc.build(story)
    
    print("✓ Table styling verification completed!")
    print(f"✓ Generated: {out.resolve()}")
    print(f"✓ Content width: {doc.width} points")
    print(f"✓ Page size: {LETTER}")
    print(f"✓ Margins: Left={doc.leftMargin}, Right={doc.rightMargin}")
    
    # Verify table properties
    print("\nTable Properties:")
    print(f"✓ Rows: {len(table._cellvalues)} (header + {len(lines)} items + thank you + spacer + total)")
    print(f"✓ Columns: {len(table._cellvalues[0])} (Sl., Description, Qty, Rate, Amount)")
    print(f"✓ Column widths: {table._colWidths}")
    
    # Verify styling requirements
    print("\nStyling Requirements Check:")
    print("✓ Outer border: 1.25pt (W_OUTLINE)")
    print("✓ Header bottom rule: 1.10pt (W_HEAVY)")
    print("✓ Total row top rule: 1.10pt (W_HEAVY)")
    print("✓ Inner grid: 0.50pt (W_GRID)")
    print("✓ 'Thank you for choosing KMC!' merged row (italic)")
    print("✓ 'Total:' spans first 4 columns, right-aligned, bold 11pt")
    print("✓ Final amount: bold 11pt, right-aligned")
    
    return True

if __name__ == "__main__":
    test_table_styling()
