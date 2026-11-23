#!/usr/bin/env sh
cd "$(dirname "$0")" || exit 1
if [ ! -d ".venv" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv .venv
  else
    echo "Python 3 not found. Please install Python 3.10+ and try again."
    exit 1
  fi
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python -m playwright install chromium --no-shell
fi
.venv/bin/python app.py
