# Локальная сборка Windows x64
# Запуск: powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed `
  --name "Neo Parser" `
  --icon "assets/icon.ico" `
  --add-data "assets/icon.png;assets" `
  --add-data "assets/icon.ico;assets" `
  --collect-all PySide6 `
  --collect-all shiboken6 `
  main.py

Write-Host "OK → dist\Neo Parser.exe"
Get-Item "dist\Neo Parser.exe" | Format-List FullName, Length
