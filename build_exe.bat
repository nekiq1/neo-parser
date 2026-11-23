@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv not found. Creating virtual environment...
  python -m venv .venv || (echo Failed to create venv. Install Python 3.10+ from python.org & pause & exit /b 1)
  echo Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  ".venv\Scripts\python.exe" -m playwright install chromium --no-shell
)
.venv\Scripts\python.exe -m pip install --upgrade pyinstaller
.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --noconsole `
  --name "Neo parser" `
  --add-data "static;static" `
  --add-data "assets;assets" `
  --collect-all playwright `
  --collect-all webview `
  --distpath "dist" `
  --workpath "build" `
  --specpath "." `
  app.py
if errorlevel 1 (echo Ошибка сборки & pause & exit /b 1)
echo Готово: dist\Neo parser\Neo parser.exe
echo Chromium будет загружен автоматически при первой проверке браузера.
pause
