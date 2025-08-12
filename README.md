# KMC Invoice (Windows-first)

Offline invoicing app built with PySide6 (Qt), ReportLab (PDF), SQLModel/SQLite, and PyInstaller.

Targets Windows for packaging and printing, but runs fine on macOS/Linux for development and tests.

- Source code: `app/`
- Assets: `assets/` (optional `logo.png`, optional `fonts/`)
- Runtime config: `settings.json`

## Features

- Create invoices and store them locally in SQLite (no Internet required)
- High-quality, code-drawn PDFs (no overlay/template files)
- Auto-increment invoice numbers with configurable prefix (e.g., `KMC-`)
- Manage customers (search, import/export CSV). Safe delete by default; optional force/cascade
- Print via the system’s default PDF handler (Windows)

## Requirements

- Python 3.9+ (see `pyproject.toml` → `requires-python = ">=3.9"`)
- Windows PowerShell (for commands below). POSIX shells are supported for dev

## Quick start (Windows PowerShell)

1. Create and activate a virtual environment

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

If activation is blocked, once per machine run in an elevated PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

1. Install dependencies

```powershell
pip install -r requirements.txt
```

1. Launch the app

```powershell
python -m app.main    # recommended (runs as a module)
# or
python app/main.py
```

PDFs default to `~/Documents/KMC Invoices` unless you choose a location in the Save dialog.

## macOS/Linux (POSIX) equivalents

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Data locations

The app reads/writes in a user‑writable folder:

- Development runs: repo root (`kmc-invoice/`) for `kmc.db` and `settings.json`
- Packaged EXE: next to `KMC Invoice.exe`

## Settings and branding

- `settings.json` stores business name, owner, phone, PAN/permit, invoice prefix, etc.
- Optional branding assets:
  - `assets/logo.png` (if present, placed on PDFs)
  - `assets/fonts/` (e.g., `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf`); falls back to Helvetica if missing

## Keyboard shortcuts

- Enter/Return: Add an item row (when focus is in the items widget)
- Delete: Remove the focused item row
- Tab order flows Bill To → first item description

## Customers: safe vs. force delete

- Safe delete warns when invoices exist
- “Delete anyway?” performs a force delete that cascades through invoices and line items

## Printing (Windows)

- Uses `os.startfile(path, "print")` to send PDFs to your default PDF app/printer
- If automatic printing fails, the PDF is opened for manual printing

## Tests

Run tests (inside the venv):

```powershell
python -m pytest -q
```

The PDF test (`tests/test_invoice_pdf.py`) verifies A4 size and key text like `Date:` and `Total:`.

## Developer utilities

- `tools/smoke_test.py` — quick DB + invoice creation sanity check
- `tools/test_invoice_table.py`, `tools/verify_table_styling.py` — layout verification helpers
- `tools/diagnostics.py` — environment and config diagnostics

## Build a Windows EXE

Option A — one-liner script (recommended):

```powershell
./tools/build.ps1
```

This creates a local venv (if missing), installs deps, and builds a GUI EXE with PyInstaller. Output goes to `dist/`.

Option B — manual PyInstaller command:

```powershell
pyinstaller --noconfirm --clean ^
  --name "KMC Invoice" --noconsole ^
  --hidden-import sqlalchemy ^
  --hidden-import pydantic ^
  --hidden-import PySide6.QtPdf ^
  --hidden-import PySide6.QtPdfWidgets ^
  --add-data "assets;assets" --add-data "settings.json;." ^
  app/main.py
```

Option C — use the spec file:

```powershell
pyinstaller tools/build.spec
```

Notes:

- Invoices are fully code‑drawn; no template/overlay files are required
- Assets (logo, fonts) and `settings.json` are bundled by the script/spec
- At runtime, resources resolve via PyInstaller’s `_MEIPASS` (bundled) or the project root (dev)

## Troubleshooting

- Virtual env won’t activate: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once in elevated PowerShell
- Missing modules (e.g., PySide6): ensure the venv is active, then `pip install -r requirements.txt`
- Printing issues: make sure a default PDF app is installed and associated with `.pdf`

## License

Private project. All rights reserved.
