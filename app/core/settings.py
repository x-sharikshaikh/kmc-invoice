from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union
import json


# Path to the repo root settings.json (…/kmc-invoice/settings.json)
SETTINGS_PATH = Path(__file__).resolve().parents[2] / "settings.json"


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
	tax_rate: float = 0.00

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

