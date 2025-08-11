from app.data.db import create_db_and_tables

if __name__ == "__main__":
    create_db_and_tables()
    print("Migration run complete")
