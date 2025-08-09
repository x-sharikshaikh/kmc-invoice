# KMC Invoice App

Windows-only offline invoice app using PySide6, ReportLab, SQLModel/SQLite, and PyInstaller.

- App code: `app/`
- Assets: `assets/` (paste your `template.pdf` and `logo.png` later)
- Settings: `settings.json`

How to set up (Windows PowerShell):
1. Optional: create/activate a virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python app/main.py`

PDFs save to `~/Documents/KMC Invoices`. Printing uses the default Windows PDF handler.
