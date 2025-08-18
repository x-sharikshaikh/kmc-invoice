from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union
import json


from app.core.paths import settings_path

# Path to the settings.json (runtime-aware)
SETTINGS_PATH = settings_path()


@dataclass
class Settings:
	business_name: str = "KMC Electrical"
	owner: str = "SHAIKH MO.AJAZ"
	phone: str = "9998714499"
	permit: str = "G-GW-E-000025-NTC(W)2018"
	pan: str = "DTPPS1809N"
	cheque_to: str = "Shaikh Mo.Ajaz"
	thank_you: str = "Thank you for choosing KMC!"
	invoice_prefix: str = "KMC-"
	# Optional absolute/relative path to a logo image
	logo_path: Optional[str] = None
	# Optional right-side name/logo image shown at top-right of the PDF
	name_logo_path: Optional[str] = None
	# Optional digital signature image placed inside the signatory box
	signature_path: Optional[str] = None
	# Optional service title/tagline shown under owner name when right logo image is not set
	service_title: str = "ELECTRICAL WORK"
	# Remember last used folder for "Save PDF" dialog
	last_pdf_dir: Optional[str] = None
	# Phase 3: file naming and archive organization
	# Template supports {number}, {date}, {customer}, {phone}
	file_name_template: str = "{number} - {customer}"
	# Optional root directory for saving PDFs; if None, defaults to Documents/KMC Invoices
	archive_root: Optional[str] = None
	# When True, create a subfolder per year under the archive root
	archive_by_year: bool = True
	# Phase 4: compact mode for denser UI
	compact_mode: bool = False

	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> "Settings":
		# Merge provided values over defaults, ignore unknown keys
		defaults = asdict(cls())
		merged: Dict[str, Any] = {**defaults, **{k: v for k, v in data.items() if k in defaults}}
		return cls(**merged)

	def to_dict(self) -> Dict[str, Any]:
		return asdict(self)


def _coerce_path(path: Optional[Union[str, Path]]) -> Path:
	return Path(path) if path is not None else SETTINGS_PATH


def load_settings(path: Optional[Union[str, Path]] = None) -> Settings:
	"""
	Load settings from JSON (UTF-8). If the file is missing, write defaults and return them.
	"""
	p = _coerce_path(path)
	if not p.exists():
		settings = Settings()
		save_settings(settings, p)
		return settings

	try:
		with p.open("r", encoding="utf-8") as f:
			raw: Dict[str, Any] = json.load(f)
	except (json.JSONDecodeError, OSError):
		# If unreadable/corrupt, fall back to defaults (do not overwrite automatically)
		return Settings()

	return Settings.from_dict(raw if isinstance(raw, dict) else {})


def save_settings(settings: Settings, path: Optional[Union[str, Path]] = None) -> None:
	"""Save settings to JSON (UTF-8), creating parent dirs if needed."""
	p = _coerce_path(path)
	p.parent.mkdir(parents=True, exist_ok=True)
	# Pretty JSON, keep Unicode
	tmp = p.with_suffix(p.suffix + ".tmp")
	with tmp.open("w", encoding="utf-8", newline="\n") as f:
		json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
		f.write("\n")
	tmp.replace(p)

