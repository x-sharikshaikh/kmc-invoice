from __future__ import annotations

from typing import Any

try:  # Optional SQLAlchemy import for Session.execute compatibility
	from sqlalchemy import text as _sa_text  # type: ignore
except Exception:  # pragma: no cover - optional dependency handling
	_sa_text = None  # type: ignore


def _exec(db_session: Any, sql: str, params: dict | None = None):
	params = params or {}
	if _sa_text is not None:
		try:
			return db_session.execute(_sa_text(sql), params)
		except Exception:
			# Fall back to raw string execution (sqlite3 cursor-like)
			pass
	return db_session.execute(sql, params)  # type: ignore[attr-defined]


def _ensure_table(db_session: Any) -> None:
	"""Create the sequences table if it doesn't exist (SQLite-safe)."""
	# Raw SQL keeps this independent of ORM models.
	sql = (
		"CREATE TABLE IF NOT EXISTS invoice_sequences ("
		" prefix TEXT PRIMARY KEY,"
		" last INTEGER NOT NULL"
		")"
	)
	_exec(db_session, sql)


def _format(prefix: str, n: int, width: int = 4) -> str:
	return f"{prefix}{n:0{width}d}"


def next_invoice_number(prefix: str, db_session: Any) -> str:
	"""
	Return the next sequential invoice number like 'KMC-0001', persisted in DB.

	Expects a SQLAlchemy/SQLModel Session or Connection-like object with:
	- execute(sql, params?)
	- commit()
	"""
	_ensure_table(db_session)

	# Try to atomically increment; if no row, insert starting at 1.
	# This two-step approach is adequate for a local offline app.
	updated = _exec(
		db_session,
		"UPDATE invoice_sequences SET last = last + 1 WHERE prefix = :p",
		{"p": prefix},
	)

	if getattr(updated, "rowcount", 0) == 0:
		# Insert starting value
		_exec(
			db_session,
			"INSERT INTO invoice_sequences(prefix, last) VALUES (:p, :val)",
			{"p": prefix, "val": 1},
		)
		current = 1
	else:
		# Fetch the new value
		row = _exec(
			db_session,
			"SELECT last FROM invoice_sequences WHERE prefix = :p",
			{"p": prefix},
		).fetchone()
		current = int(row[0]) if row else 1

	# Persist
	if hasattr(db_session, "commit"):
		db_session.commit()

	return _format(prefix, current)

