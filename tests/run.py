"""Мини-раннер без зависимостей: python tests/run.py (работает и с pytest)."""
import sys, importlib, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
ok = bad = 0
for mod in (sys.argv[1:] or ["test_core", "test_ai", "test_api", "test_scraper"]):
    m = importlib.import_module(mod)
    for n in sorted(dir(m)):
        if n.startswith("test_"):
            try:
                getattr(m, n)(); ok += 1; print("OK  ", mod, n)
            except Exception:
                bad += 1; print("FAIL", mod, n); traceback.print_exc()
print(f"\n{ok} passed, {bad} failed"); sys.exit(1 if bad else 0)
