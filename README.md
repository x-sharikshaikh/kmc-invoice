# KMC Invoice App

Windows-only offline invoice app using PySide6, ReportLab, SQLModel/SQLite, and PyInstaller.

- App code: `app/`
- Assets: `assets/` (add your `logo.png` and optional `fonts/`)
- Settings: `settings.json`

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
python tools/make_sample_pdf.py
```

## Build a Windows EXE

Two options:

- Quick command (PowerShell):
  - Ensure dependencies are installed: `pip install -r requirements.txt`
  - Build: `pyinstaller --noconfirm --clean --name "KMC Invoice" --noconsole --hidden-import sqlalchemy --hidden-import pydantic --add-data "assets;assets" --add-data "settings.json;." app/main.py`
  - Output: `dist/KMC Invoice/KMC Invoice.exe`

- With spec file:
  - `pyinstaller tools/build.spec`

### Notes

- Template PDF is no longer required; invoices are fully code-drawn via ReportLab.
- Assets (logo.png, fonts) are bundled under `assets/`.
- `settings.json` is placed next to the EXE on first run if missing. You can edit it there.
- At runtime the app resolves resources using PyInstaller's _MEIPASS or project root in dev.
