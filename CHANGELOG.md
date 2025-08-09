# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-08-09

### Added

- PySide6 desktop app for creating invoices (Windows).
- SQLModel/SQLite storage for Customers, Invoices, and Items.
- Automatic invoice numbering (peek next on load; increment on save).
- Settings dialog to manage business info, invoice prefix, tax rate, and logo.
- Light QSS theme with rounded corners and bold centered table headers; optional dark mode.
- PDF generation with ReportLab overlay and template merge via pypdf.
- A4 single-page invoice with right-aligned numeric columns.
- Resource path helpers compatible with dev and PyInstaller (_MEIPASS).
- PyInstaller build spec and PowerShell build script bundling assets and fonts.
- Customers dialog with search and "Use selected" to prefill BILL TO.
- Export/Import: settings.json (Settings dialog) and customers CSV (Customers dialog).
- Overlay offset tuning via `assets/overlay_offsets.json` for quick coordinate nudging.

### Fixed

- SQLAlchemy mapper error by using SQLModel Relationship hints and pinning compatible deps.
- Multiple UI indentation issues; stabilized signal wiring and layout.

### Tests

- Pytest covering overlay + merge: verifies A4 single page and presence of date/total text.

### Notes

- Dependencies pinned for compatibility: sqlmodel==0.0.8; sqlalchemy>=1.4,<2.0; pydantic>=1.10,<2.0.
- PDFs are saved under `~/Documents/KMC Invoices` by default.
