from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_path() -> Path:
    """Return the base path for bundled resources (assets) depending on runtime.

    - In PyInstaller onefile, resources are extracted to sys._MEIPASS.
    - In dev, use project root (…/kmc-invoice).
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parents[2]


def resource_path(rel: str | Path) -> Path:
    """Resolve a resource path (e.g., 'assets/logo.png') for current runtime."""
    rel = Path(rel)
    return base_path() / rel


def user_writable_dir() -> Path:
    """Directory suitable for user-writable files (like settings.json).

    - In PyInstaller onefile, prefer the directory containing the executable.
    - In dev, use the project root.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def settings_path() -> Path:
    """Location for settings.json that is readable and writable."""
    return user_writable_dir() / "settings.json"
