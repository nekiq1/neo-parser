"""Application configuration and constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path.home() / ".neo_parser"
APP_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("NEO_PARSER_DB", str(APP_DIR / "neo_parser.sqlite3")))
SETTINGS_PATH = APP_DIR / "settings.json"
LOG_PATH = APP_DIR / "neo_parser.log"

# 2GIS
TWOGIS_API_KEY = os.getenv("TWOGIS_API_KEY", "").strip()
TWOGIS_BASE = "https://catalog.api.2gis.com"
TWOGIS_MAX_PAGES = int(os.getenv("TWOGIS_MAX_PAGES", "5"))
AUDIT_TIMEOUT = int(os.getenv("AUDIT_TIMEOUT", "10"))

# Region IDs (2GIS region_id for Places / Markers API)
# Source: https://docs.2gis.com — region/search
CITIES = {
    "Москва": {"region_id": "32", "center": "37.622161,55.751597"},
    "Московская область": {"region_id": "32", "center": "37.622161,55.751597"},
    "Санкт-Петербург": {"region_id": "1", "center": "30.314278,59.938732"},
    "Ленинградская область": {"region_id": "1", "center": "30.314278,59.938732"},
}

DEFAULT_NICHES = [
    "Мебель на заказ",
    "Торговое оборудование",
    "Мебель для салонов и клиник",
    "Стойки ресепшн",
    "Лофты",
    "Фотостудии",
    "Ландшафтный дизайн",
    "Металлоконструкции",
]

# CRM statuses
STATUSES = [
    "Новый",
    "Проверен",
    "Готов к обращению",
    "Написал",
    "Ответил",
    "Переговоры",
    "Клиент",
    "Отказ",
]


def get_api_key() -> str:
    """Return API key from env or settings file."""
    if TWOGIS_API_KEY:
        return TWOGIS_API_KEY
    if SETTINGS_PATH.exists():
        try:
            import json

            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            return (data.get("twogis_api_key") or "").strip()
        except Exception:
            pass
    return ""


def save_api_key(key: str) -> None:
    import json

    data = {}
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["twogis_api_key"] = key.strip()
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
