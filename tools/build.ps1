# Build KMC Invoice (Windows)
# Requires: Python, pip, PyInstaller

$ErrorActionPreference = 'Stop'

Write-Host 'Installing dependencies...'
pip install -r ..\requirements.txt | Out-Host

Write-Host 'Building onefile executable...'
pyinstaller --noconfirm --clean `
    --name "KMC Invoice" `
    --noconsole `
    --hidden-import sqlalchemy --hidden-import pydantic `
    --add-data "assets;assets" `
    --add-data "settings.json;." `
    app/main.py | Out-Host

Write-Host 'Done. Output in dist\\KMC Invoice\\'
