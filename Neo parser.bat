@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Первый запуск: установка зависимостей...
  python -m venv .venv || (echo Установите Python 3.10+ с python.org & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  ".venv\Scripts\python.exe" -m playwright install chromium --no-shell
)
".venv\Scripts\python.exe" app.py
pause
