"""
Invoice PDF Generator using the new table layout system.
This file demonstrates how to use build_invoice_table with Platypus.
"""

from app.pdf.table_layout import build_invoice_table
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import LETTER
from pathlib import Path

def generate_sample_invoice(output_path: str):
    """
    Generate a sample invoice using the new table layout system.
    
    Args:
        output_path: Path where the PDF should be saved
    """
    # Sample invoice data
    lines = [
        {"sl": "1.", "description": "Electrical inspection and diagnostics", "qty": 1, "rate": 120.00, "amount": 120.00},
        {"sl": "2.", "description": "Wiring repair (per room)", "qty": 2, "rate": 85.50, "amount": 171.00},
        {"sl": "3.", "description": "LED fixture installation", "qty": 3, "rate": 45.00, "amount": 135.00},
        {"sl": "4.", "description": "Breaker replacement", "qty": 1, "rate": 65.75, "amount": 65.75},
        {"sl": "5.", "description": "Safety compliance testing", "qty": 1, "rate": 90.00, "amount": 90.00},
    ]
    total_amt = sum(r["amount"] for r in lines)

    # Create the document
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=LETTER, 
        leftMargin=36, 
        rightMargin=36, 
        topMargin=36, 
        bottomMargin=54
    )

    # Build the story (content)
    story = []
    story.append(build_invoice_table(lines, total=total_amt))
    story.append(Spacer(1, 12))

    # Build the PDF
    doc.build(story)

if __name__ == "__main__":
    # Example usage
    output_file = "sample_invoice.pdf"
    generate_sample_invoice(output_file)
    print(f"Sample invoice generated: {output_file}")
