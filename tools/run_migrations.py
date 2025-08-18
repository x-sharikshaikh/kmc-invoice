from pathlib import Path
import sys

# Ensure project root is on sys.path when running directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.db import create_db_and_tables

if __name__ == "__main__":
    create_db_and_tables()
    print("Migration run complete")
