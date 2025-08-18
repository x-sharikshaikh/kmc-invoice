from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


pytest.importorskip("pytestqt")


def test_app_window_creation(qtbot):  # type: ignore[reportUnknownParameterType]
    # Ensure single QApplication
    app = QApplication.instance() or QApplication([])
    from app.ui_main import create_main_window
    win = create_main_window()
    qtbot.addWidget(win)
    assert hasattr(win, "stack"), "Shell stack should exist"
    assert hasattr(win, "footer"), "Footer bar should exist"
    # Invoice view at index 0
    assert win.stack.currentIndex() == 0
    # Buttons are proxied from editor
    assert hasattr(win, "btn_save_pdf") and win.btn_save_pdf is not None
