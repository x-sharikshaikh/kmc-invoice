from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


def placeholder(name: str) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.addWidget(QLabel(f"{name} — Coming in Phase 2/3"))
    v.addStretch(1)
    return w
