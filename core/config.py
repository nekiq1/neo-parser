"""Пути и настройки (settings.json рядом с программой / EXE)."""
import json, os, sys
from pathlib import Path

APP_NAME = "Neo parser"
VERSION = "1.1.0"
FROZEN = getattr(sys, "frozen", False)


def app_dir() -> Path:
    return Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent.parent


ROOT = app_dir()                                              # рядом с EXE: базы, настройки, browsers
RES = Path(getattr(sys, "_MEIPASS", ROOT)) if FROZEN else ROOT  # ресурсы внутри сборки: static, assets
DB_DIR, SITES_DIR, LOG_DIR = ROOT / "databases", ROOT / "websites", ROOT / "logs"
ASSETS, STATIC = RES / "assets", RES / "static"
SETTINGS_FILE, SENT_FILE, LOG_FILE = ROOT / "settings.json", ROOT / "sent.json", LOG_DIR / "neo.log"

DEFAULTS = {
    "headless": False, "max_results": 0, "parallel_workers": 3,
    "deep_contact_search": True, "geo_grid_search": True,
    "delay_min": 0.6, "delay_max": 1.6,
    "ai_provider": "DeepSeek", "deepseek_api_key": "", "deepseek_model": "deepseek-chat",
    "gemini_api_key": "", "gemini_model": "gemini-3.8-flash",
    "outreach_template": "Здравствуйте! Меня зовут ... Увидел(а) «{name}» на Яндекс Картах и хочу предложить вам ...",
}
_LIMITS = {"parallel_workers": (1, 8), "max_results": (0, 100000)}
SECRET_KEYS = ("deepseek_api_key", "gemini_api_key")


def load_settings() -> dict:
    s = dict(DEFAULTS)
    try:
        s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    # Gemini 2.5 Flash is access-restricted for projects without prior usage.
    # Migrate the old application default so existing settings.json files do not
    # keep calling a model that the user's project may not be allowed to use.
    if str(s.get("gemini_model", "")).strip() == "gemini-2.5-flash":
        s["gemini_model"] = "gemini-3.8-flash"
    return s


def public_settings() -> dict:
    """Для UI: секреты не отдаём, только признак что ключ задан."""
    s = load_settings()
    for k in SECRET_KEYS:
        s[k + "_set"] = bool(s.get(k))
        s[k] = ""
    return s


def save_settings(new: dict) -> dict:
    s = load_settings()
    for k, default in DEFAULTS.items():
        if k not in new:
            continue
        v = new[k]
        if k in SECRET_KEYS and not v:        # пустое поле — оставить прежний ключ
            continue
        try:
            if isinstance(default, bool): v = bool(v)
            elif isinstance(default, int): v = int(v)
            elif isinstance(default, float): v = float(v)
            else: v = str(v)[:2000]
        except (TypeError, ValueError):
            continue
        if k in _LIMITS:
            lo, hi = _LIMITS[k]; v = max(lo, min(hi, v))
        s[k] = v
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, SETTINGS_FILE)
    return s


def ensure_dirs():
    for d in (DB_DIR, SITES_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
