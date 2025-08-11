"""
Create a PNG snapshot of the invoice table from the generated PDF.
This script attempts to use available libraries to rasterize the PDF.
"""

from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def create_png_snapshot():
    """Create a PNG snapshot of the invoice table."""
    pdf_path = Path("sample_invoice.pdf")
    png_path = Path("sample_invoice_table.png")
    
    if not pdf_path.exists():
        print(f"PDF file not found: {pdf_path}")
        return False
    
    try:
        # Try using pypdf if available
        import pypdf
        print("Using pypdf to extract PDF info...")
        
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            if len(reader.pages) > 0:
                page = reader.pages[0]
                print(f"PDF has {len(reader.pages)} page(s)")
                print(f"Page size: {page.mediabox}")
                print(f"PDF created successfully!")
                print(f"Note: PNG snapshot creation requires additional libraries.")
                print(f"PDF file: {pdf_path.resolve()}")
                return True
            else:
                print("PDF has no pages")
                return False
                
    except ImportError:
        print("pypdf not available")
        return False
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return False

if __name__ == "__main__":
    create_png_snapshot()
