from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager

from sqlmodel import SQLModel, Session, create_engine


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
	SQLModel.metadata.create_all(engine)


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

