#!/usr/bin/env bash
# Сборка DMG для macOS Apple Silicon (M1 / M2 / M3 / M4)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Запускайте на macOS."
  exit 1
fi
if [ "$(uname -m)" != "arm64" ]; then
  echo "Нужен Apple Silicon (M1+). Сейчас: $(uname -m)"
  exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed \
  --name "Neo Parser" \
  --icon "assets/icon.png" \
  --add-data "assets/icon.png:assets" \
  --osx-bundle-identifier com.neki.neoparser \
  --collect-all PySide6 \
  --collect-all shiboken6 \
  main.py

test -x "dist/Neo Parser.app/Contents/MacOS/Neo Parser"
file "dist/Neo Parser.app/Contents/MacOS/Neo Parser" | grep -qi arm64

codesign --force --deep --sign - "dist/Neo Parser.app" || true

hdiutil create \
  -volname "Neo Parser" \
  -srcfolder "dist/Neo Parser.app" \
  -ov -format UDZO \
  "dist/Neo-Parser-macOS-Apple-Silicon-arm64.dmg"

echo ""
echo "Готово: dist/Neo-Parser-macOS-Apple-Silicon-arm64.dmg"
ls -lh "dist/Neo-Parser-macOS-Apple-Silicon-arm64.dmg"
