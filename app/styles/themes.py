from __future__ import annotations

from app.styles.tokens import Colors, Radius, Space


def light_qss() -> str:
    c = Colors
    r = Radius
    s = Space
    return f"""
    QWidget {{ font-size: 13px; background: {c.bg}; color: {c.text}; }}
    QMainWindow>QWidget {{ background: {c.bg}; }}
    QFrame#Card {{ border: 1px solid {c.border}; border-radius: {r.md}px; background: {c.card}; }}
    QFrame#CardRow {{ border:1px solid {c.border}; border-radius:{r.md}px; background:{c.card}; padding:{s.sm}px; }}
    QFrame#CardRow:focus-within {{ border-color:{c.primary}; }}
    QLabel#SectionTitle {{ font-size: 14px; font-weight: 700; color: {c.subtext}; padding: 2px 2px 0 2px; }}
    QLabel {{ font-size: 13px; }}
    QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox {{
        border: 1px solid {c.input_border}; border-radius: {r.md}px; padding: {s.sm}px; background: {c.card};
    }}
    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus {{ border: 1px solid {c.primary}; }}
    QPushButton {{ padding: 9px 16px; border-radius: {r.md}px; border: 1px solid {c.border}; background: {c.card}; }}
    QPushButton:hover {{ background: #f3f6ff; border-color: #b8c6ff; }}
    QPushButton:pressed {{ background: #e8eeff; }}
    /* Nav rail */
    QWidget#NavRail {{ background: #ffffff; border-right: 1px solid {c.border}; }}
    QPushButton#NavButton {{ border:none; text-align:left; padding:8px 12px; border-radius:{r.sm}px; }}
    QPushButton#NavButton:hover {{ background:#eef2ff; }}
    QPushButton#NavButton:checked {{ background:#e6ecff; color:#234; font-weight:600; }}
    /* Sticky footer */
    QWidget#FooterBar {{ background:#ffffff; border-top:1px solid {c.border}; }}
    """


def dark_qss() -> str:
    c = Colors
    r = Radius
    s = Space
    return f"""
    QWidget {{ font-size: 13px; background: {c.bg_dark}; color: {c.text_dark}; }}
    QMainWindow>QWidget {{ background: {c.bg_dark}; }}
    QFrame#Card {{ border: 1px solid {c.border_dark}; border-radius: {r.md}px; background: {c.card_dark}; }}
    QFrame#CardRow {{ border:1px solid #555; border-radius:{r.md}px; background:#3a3a3a; padding:{s.sm}px; }}
    QFrame#CardRow:focus-within {{ border-color: {c.primary_dark}; }}
    QLabel#SectionTitle {{ font-size: 14px; font-weight: 700; color: {c.text_dark}; padding: 2px 2px 0 2px; }}
    QLabel {{ font-size: 13px; color: {c.text_dark}; }}
    QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox {{
        border: 1px solid {c.input_border_dark}; border-radius: {r.md}px; padding: {s.sm}px; background: #2e2e2e; color:{c.text_dark};
    }}
    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus {{ border: 1px solid {c.primary_dark}; }}
    QPushButton {{ padding: 9px 16px; border-radius: {r.md}px; border: 1px solid {c.input_border_dark}; background: #3a3a3a; color: {c.text_dark}; }}
    QPushButton:hover {{ background: #414141; border-color: #6a6a6a; }}
    QPushButton:pressed {{ background: #3c3c3c; }}
    /* Nav rail */
    QWidget#NavRail {{ background: #2f2f2f; border-right: 1px solid {c.border_dark}; }}
    QPushButton#NavButton {{ border:none; text-align:left; padding:8px 12px; border-radius:{r.sm}px; }}
    QPushButton#NavButton:hover {{ background:#3a3f55; }}
    QPushButton#NavButton:checked {{ background:#3f4566; color:#eaf; font-weight:600; }}
    QWidget#FooterBar {{ background:#2f2f2f; border-top:1px solid {c.border_dark}; }}
    """
