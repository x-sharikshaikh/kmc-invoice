from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text, MetaData


# Project root (…/kmc-invoice)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "kmc.db"

_ENGINE = None


def get_engine(echo: bool = False):
	"""Return a singleton SQLAlchemy engine for the project SQLite DB."""
	global _ENGINE
	if _ENGINE is None:
		# Use posix path for SQLAlchemy URL compatibility on Windows
		url = f"sqlite:///{DB_PATH.as_posix()}"
		_ENGINE = create_engine(url, echo=echo, connect_args={"check_same_thread": False})
	return _ENGINE


def create_db_and_tables(echo: bool = False) -> None:
	"""Create the SQLite database file and all SQLModel tables."""
	# Ensure models are imported so metadata has all tables
	import app.data.models  # noqa: F401

	engine = get_engine(echo=echo)
	DB_PATH.parent.mkdir(parents=True, exist_ok=True)
	# Create any missing tables
	SQLModel.metadata.create_all(engine)
	# Run lightweight migrations
	_migrate_drop_invoice_tax(engine)
	_migrate_drop_invoice_subtotal(engine)


def _migrate_drop_invoice_tax(engine) -> None:
	"""Drop the legacy Invoice.tax column if it still exists.

	Strategy:
	- If SQLite supports DROP COLUMN (>=3.35), use ALTER TABLE.
	- Otherwise, rebuild the table using the current SQLModel schema:
	  create a new table with the updated schema, copy data, drop old, rename new.
	"""
	try:
		with engine.begin() as conn:
			# Detect if column exists
			cols = conn.exec_driver_sql("PRAGMA table_info('invoice')").all()
			col_names = {row[1] for row in cols}
			if 'tax' not in col_names:
				return  # nothing to do

			# Determine SQLite version
			ver_row = conn.exec_driver_sql("select sqlite_version()").first()
			version = ver_row[0] if ver_row else "0.0.0"
			def _ver_tuple(v: str) -> tuple[int, int, int]:
				try:
					parts = (v or "").split(".")
					return (int(parts[0]), int(parts[1]), int(parts[2]))
				except Exception:
					return (0, 0, 0)
			if _ver_tuple(version) >= (3, 35, 0):
				# Modern SQLite: use DROP COLUMN
				conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
				conn.exec_driver_sql("ALTER TABLE invoice DROP COLUMN tax")
				conn.exec_driver_sql("PRAGMA foreign_keys=ON")
				return

		# Fallback: rebuild table with SQLAlchemy/SQLModel (without 'tax')
		from sqlmodel import SQLModel
		from sqlalchemy import Table
		import app.data.models  # ensure models loaded

		with engine.begin() as conn:
			conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

			# Create a new table with the updated schema named invoice_new
			old = SQLModel.metadata.tables.get('invoice')
			if old is None:
				# If invoice table is not registered (unlikely), nothing to do
				conn.exec_driver_sql("PRAGMA foreign_keys=ON")
				return
			new_meta = MetaData()
			new_table = old.tometadata(new_meta, name='invoice_new')
			new_table.create(conn)

			# Copy over columns present in the new schema, inserting NULL for any new columns
			# that do not exist in the old table.
			old_cols_rows = conn.exec_driver_sql("PRAGMA table_info('invoice')").all()
			old_col_names = {row[1] for row in old_cols_rows}
			new_cols = [c.name for c in new_table.columns]
			cols_csv = ", ".join(new_cols)
			select_parts = [
				(name if name in old_col_names else f"NULL AS {name}")
				for name in new_cols
			]
			cols_csv_sel = ", ".join(select_parts)
			conn.exec_driver_sql(
				f"INSERT INTO invoice_new ({cols_csv}) SELECT {cols_csv_sel} FROM invoice"
			)

			# Drop old and rename new
			conn.exec_driver_sql("DROP TABLE invoice")
			conn.exec_driver_sql("ALTER TABLE invoice_new RENAME TO invoice")
			conn.exec_driver_sql("PRAGMA foreign_keys=ON")
	except Exception:
		# Do not block app startup if migration fails; leave old column in place
		pass


def _migrate_drop_invoice_subtotal(engine) -> None:
	"""Drop the legacy Invoice.subtotal column if present.

	Uses the same strategy as dropping tax.
	"""
	try:
		with engine.begin() as conn:
			cols = conn.exec_driver_sql("PRAGMA table_info('invoice')").all()
			col_names = {row[1] for row in cols}
			if 'subtotal' not in col_names:
				return

		# Rebuild table with updated schema
		from sqlmodel import SQLModel
		import app.data.models  # ensure models loaded
		from sqlalchemy import MetaData

		with engine.begin() as conn:
			conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
			old = SQLModel.metadata.tables.get('invoice')
			if old is None:
				conn.exec_driver_sql("PRAGMA foreign_keys=ON")
				return
			new_meta = MetaData()
			new_table = old.tometadata(new_meta, name='invoice_new')
			new_table.create(conn)

			# Copy with NULLs for any new columns not present in the old schema
			old_cols_rows = conn.exec_driver_sql("PRAGMA table_info('invoice')").all()
			old_col_names = {row[1] for row in old_cols_rows}
			new_cols = [c.name for c in new_table.columns]
			cols_csv = ", ".join(new_cols)
			select_parts = [
				(name if name in old_col_names else f"NULL AS {name}")
				for name in new_cols
			]
			cols_csv_sel = ", ".join(select_parts)
			conn.exec_driver_sql(
				f"INSERT INTO invoice_new ({cols_csv}) SELECT {cols_csv_sel} FROM invoice"
			)
			conn.exec_driver_sql("DROP TABLE invoice")
			conn.exec_driver_sql("ALTER TABLE invoice_new RENAME TO invoice")
			conn.exec_driver_sql("PRAGMA foreign_keys=ON")
	except Exception:
		pass


def get_session(echo: bool = False) -> Session:
	"""Create a new SQLModel Session bound to the project engine.

	expire_on_commit=False so returned instances keep attribute values after commit
	(avoids refresh on closed sessions when callers use detached instances).
	"""
	return Session(get_engine(echo=echo), expire_on_commit=False)


@contextmanager
def session_scope(echo: bool = False) -> Generator[Session, None, None]:
	"""Context manager-style generator for sessions.

	Usage:
		with session_scope() as s:
			... use s ...
	"""
	session = get_session(echo=echo)
	try:
		yield session
		session.commit()
	except Exception:
		session.rollback()
		raise
	finally:
		session.close()

