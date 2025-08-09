# KMC Invoice App

Windows-only offline invoice app using PySide6, ReportLab, SQLModel/SQLite, and PyInstaller.

- App code: `app/`
- Assets: `assets/` (add your `logo.png` and optional `fonts/`)
- Settings: `settings.json`

## Assets

- Invoices are generated fully in code using ReportLab. An external `template.pdf` is not required.
- Optional branding assets:
  - `assets/logo.png` (optional; used if present)
  - `assets/fonts/` (optional; add fonts like Noto Sans; falls back to built-in fonts if missing)
- If the logo or fonts are missing, PDF generation still works and uses defaults.

## Install & Run (Windows PowerShell)

1. Optional: create and activate a virtual environment

    ```powershell
    python -m venv .venv
    . .venv\Scripts\Activate.ps1
    ```

2. Install dependencies

    ```powershell
    pip install -r requirements.txt
    ```

3. Launch the app

    ```powershell
    python app/main.py
    ```

PDFs are saved to `~/Documents/KMC Invoices`.

### Printing

- Use the Print button to send the generated PDF to your default Windows PDF viewer/printer.
- Ensure a default PDF app (e.g., Edge, Adobe Reader) is installed and associated with .pdf files.
- You can also open the saved PDF from `~/Documents/KMC Invoices` and print manually.

## Screenshots / Samples

- App screenshot (add your own): `assets/samples/screenshot.png`
- Redacted sample PDF: `assets/samples/sample-redacted.pdf`

Generate the sample PDF:

```powershell
python tools/make_sample_pdf_drawn.py
```

## Build a Windows EXE

Two options:

- Quick command (PowerShell):
  - Ensure dependencies are installed: `pip install -r requirements.txt`
  - Build: `pyinstaller --noconfirm --clean --name "KMC Invoice" --noconsole --hidden-import sqlalchemy --hidden-import pydantic --add-data "assets;assets" --add-data "settings.json;." app/main.py`
  - Output: `dist/KMC Invoice/KMC Invoice.exe`

- With spec file:
  - `pyinstaller tools/build.spec`
    - The spec bundles `assets/` (logo/fonts) and `settings.json` only; no `template.pdf` is included.

### Notes

- Template PDF is no longer required; invoices are fully code-drawn via ReportLab. No `template.pdf` needs to be bundled.
- Assets (logo.png, fonts) are bundled under `assets/`.
- `settings.json` is placed next to the EXE on first run if missing. You can edit it there.
- At runtime the app resolves resources using PyInstaller's _MEIPASS or project root in dev.

## QA Checklist

See `tools/qa_checklist.txt` for end-to-end steps to verify pagination, formatting, printing, and packaged EXE behavior.
