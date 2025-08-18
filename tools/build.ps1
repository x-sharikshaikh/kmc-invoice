<#
 Build KMC Invoice (Windows)
 - Uses a project-local venv (./.venv)
 - Installs dependencies from requirements.txt
 - Packages with PyInstaller into a one-file GUI exe
#>

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
$req = Join-Path $root 'requirements.txt'

Write-Host "Setting up virtual environment..."
if (-not (Test-Path $venv)) {
    Write-Host "Creating venv at $venv"
    python -m venv $venv | Out-Host
}

if (-not (Test-Path $python)) {
    throw "Python executable not found in venv: $python"
}

Write-Host 'Upgrading pip...'
& $python -m pip install --upgrade pip | Out-Host

Write-Host "Installing dependencies from $req ..."
& $python -m pip install -r $req | Out-Host

Write-Host 'Building onefile executable with PyInstaller...'
Push-Location $root
try {
    & $python -m PyInstaller --noconfirm --clean `
        --name "KMC Invoice" `
        --noconsole `
        --hidden-import sqlalchemy `
        --hidden-import pydantic `
        --hidden-import PySide6.QtPdf `
        --hidden-import PySide6.QtPdfWidgets `
        --add-data "assets;assets" `
        --add-data "settings.json;." `
        app/main.py | Out-Host
}
finally {
    Pop-Location
}

Write-Host 'Done. Output in dist\\KMC Invoice\\'
