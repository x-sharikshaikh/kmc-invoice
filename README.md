# KMC Invoice (Windows)

Offline Windows invoicing app built with PySide6 (Qt), ReportLab (PDF), SQLModel/SQLite, and PyInstaller.

While the app targets Windows for packaging and printing, you can run it on other platforms for development/testing. PowerShell commands below have POSIX equivalents.

- Code: `app/`
- Assets: `assets/` (optional `logo.png`, optional `fonts/`)
- Runtime config: `settings.json`

## What it does

- Create invoices and save them to a local SQLite database (no Internet required).
- Generate high-quality, code‑drawn PDFs (no overlay/template files).
- Auto-increment invoice numbers with a configurable prefix (e.g., `KMC-`).
- Manage customers (search, import/export CSV, select). Delete safely or force delete with cascade.
- Print using the system’s default PDF handler (Windows).

## Install and run (PowerShell)

1) Create/activate a virtual environment (recommended)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Launch the app

```powershell
python -m app.main    # recommended (runs as a module)
# or
python app/main.py
```

PDFs default to `~/Documents/KMC Invoices` unless you choose a location in the Save dialog.

Data files (`kmc.db`, `settings.json`) live in a user‑writable folder:
- Packaged EXE: next to `KMC Invoice.exe`
- Dev runs: project root (`kmc-invoice/`)

## Settings and assets

- `settings.json` stores your business name, owner, phone, PAN/permit, invoice prefix, etc.
- Optional branding:
  - `assets/logo.png` (used if present)
  - `assets/fonts/` (e.g., `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf`); falls back to Helvetica if missing

## Keyboard shortcuts

- Enter/Return: Add an item row (when focus is within the items widget)
- Delete: Remove the currently focused item row
- Tab order flows through Bill To → first item description

## Customers: safe and force delete

- Delete attempts are safe by default and will warn if invoices exist.
- Click “Delete anyway?” to force delete a customer and cascade delete all their invoices and items.

## Printing (Windows)

- Uses `os.startfile(path, "print")` to send the PDF to your default PDF app/printer.
- If automatic printing fails, the app opens the PDF so you can print from your viewer.

## Tests

Run tests (requires dependencies):

```powershell
python -m pytest -q
```

The PDF test (`tests/test_invoice_pdf.py`) checks that the generated PDF is A4 sized and contains key text like `Date: …` and `Total:` values.

## Developer utilities

- `tools/smoke_test.py` — quick DB and invoice creation sanity check.
- `tools/test_invoice_table.py`, `tools/verify_table_styling.py` — layout verification helpers.

## Build a Windows EXE

Quick build:

```powershell
pyinstaller --noconfirm --clean ^
  --name "KMC Invoice" --noconsole ^
  --hidden-import sqlalchemy --hidden-import pydantic ^
  --add-data "assets;assets" --add-data "settings.json;." ^
  app/main.py
```

Or with the provided spec: `pyinstaller tools/build.spec`

Notes:
- No template/overlay files are required; invoices are fully code‑drawn (the legacy overlay code has been removed).
- Assets (logo, fonts) and `settings.json` are bundled by the spec.
- At runtime, resources resolve via PyInstaller’s `_MEIPASS` (bundled) or the project root (dev).

## Troubleshooting

- PowerShell won’t activate venv: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once in an elevated PowerShell.
- Missing PySide6 or other modules: run `pip install -r requirements.txt` inside the venv.
- Printing doesn’t work: ensure a default PDF app is installed and associated with `.pdf`.

## License

Private project. All rights reserved.
