from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget


def _show_warning(message: str, parent: Optional[QWidget] = None, title: str = "Print error") -> None:
	app = QApplication.instance()
	if app is None:
		# Fallback for non-GUI contexts
		print(f"{title}: {message}", file=sys.stderr)
		return
	QMessageBox.warning(parent, title, message)


def print_pdf(path: str, parent: Optional[QWidget] = None) -> bool:
	"""Send a PDF to the default printer on Windows using the associated viewer.

	Uses os.startfile(path, "print"). If no PDF print association exists or another
	error occurs, a friendly message box is shown. Returns True on dispatch,
	False otherwise.
	"""
	if sys.platform != "win32":
		_show_warning("Printing is supported on Windows only.", parent)
		return False

	p = Path(path)
	if not p.exists():
		_show_warning(f"File not found:\n{p}", parent)
		return False

	try:
		os.startfile(str(p), "print")  # type: ignore[attr-defined]
		return True
	except OSError as e:
		# Common case: no application associated with printing PDFs
		_show_warning(
			"Unable to print the PDF.\n\n"
			"Install a PDF viewer (e.g., Adobe Acrobat Reader) and associate .pdf files with it as the default app.\n"
			"Also ensure the viewer supports printing via the system context (Print verb).",
			parent,
		)
		return False
	except Exception as e:  # Defensive catch-all
		_show_warning(f"Unexpected error while printing:\n{e}", parent)
		return False


def open_file(path: str, parent: Optional[QWidget] = None) -> bool:
	"""Open a file with the default associated application on Windows.

	Uses os.startfile(path). Shows a friendly warning on errors. Returns True on dispatch.
	"""
	if sys.platform != "win32":
		_show_warning("Opening files is supported on Windows only.", parent, title="Open error")
		return False

	p = Path(path)
	if not p.exists():
		_show_warning(f"File not found:\n{p}", parent, title="Open error")
		return False

	try:
		os.startfile(str(p))  # type: ignore[attr-defined]
		return True
	except OSError:
		_show_warning(
			"Unable to open the file.\n\n"
			"Ensure a default application is associated with this file type.",
			parent,
			title="Open error",
		)
		return False
	except Exception as e:
		_show_warning(f"Unexpected error while opening file:\n{e}", parent, title="Open error")
		return False

