"""Neo parser — локальное приложение (Flask + собственное окно / браузер). 
Запуск: python app.py"""

import json
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime

# --- БЛОК ДЛЯ PYINSTALLER (ИСПРАВЛЯЕТ ОШИБКИ МОДУЛЕЙ И БРАУЗЕРА) ---
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    # Указываем Playwright, где лежат упакованные браузеры
    playwright_path = os.path.join(base_path, 'playwright', 'driver', 'package', '.local-browsers')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = playwright_path
    # Для корректной работы pywebview на Windows
    if sys.platform == 'win32':
        os.environ['WEBVIEW2_USER_DATA_FOLDER'] = os.path.join(os.path.expanduser('~'), '.neo_parser_webview')
# ------------------------------------------------------------------

from flask import Flask, jsonify, request, send_from_directory, send_file, abort, Response
from core import config, filters as F, export, mockups, outreach, ai
from core.yandex import YandexParser, StopRequested, CaptchaError, split_list

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")  # сборка без консоли
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

app = Flask(__name__, static_folder=None)
config.ensure_dirs()


class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.logs = []
        self.reset()

    def reset(self):
        self.running, self.stop_flag = False, False
        self.records, self.error, self.last_file = [], "", ""
        self.title, self.base = "neo", ""

    def log(self, msg):
        line = f"{datetime.now():%H:%M:%S} {msg}"
        with self.lock:
            self.logs = (self.logs + [line])[-500:]
        try:
            with open(config.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now():%Y-%m-%d} {line}\n")
        except OSError:
            pass

    def add(self, rec):
        with self.lock:
            self.records.append(rec)


JOB = Job()

CITIES, POP = [], {}
try:
    CITIES = json.loads((config.ASSETS / "cities.json").read_text(encoding="utf-8"))["cities"]
    POP = {c["name"]: c.get("population", 0) for c in CITIES}
except (OSError, ValueError, KeyError):
    pass


def _run_job(cities, rubrics, settings):
    try:
        JOB.log(f"Старт: города={cities}, рубрики={rubrics}, лимит на пару={settings['max_results'] or '∞'}")
        YandexParser(settings, JOB.log, lambda n: None, lambda: JOB.stop_flag, JOB.add).run(cities, rubrics, POP)
        JOB.log("Сбор завершён.")
    except StopRequested:
        JOB.log("Остановлено пользователем.")
    except CaptchaError as e:
        JOB.error = str(e)
        JOB.log(JOB.error)
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            msg = "Chromium не найден. Нажмите «Проверить браузер» или выполните: python -m playwright install chromium"
        elif "net::ERR" in msg:
            msg = "Сетевая ошибка: проверьте интернет-соединение."
        JOB.error = msg[:300]
        JOB.log("Ошибка: " + JOB.error)
    finally:
        with JOB.lock:
            JOB.running = False
        if JOB.records:
            try:
                p = export.save_xlsx(JOB.records, config.DB_DIR, "leads_" + JOB.title)
                JOB.last_file, JOB.base = p.name, p.name
                JOB.log(f"Сохранено: databases/{p.name} ({len(JOB.records)} орг.)")
            except Exception as e:
                JOB.log(f"Не удалось сохранить XLSX: {e}")


# ---------------- страницы и справочники ----------------
@app.get("/")
def index():
    return send_from_directory(config.STATIC, "index.html")


@app.get("/api/cities")
def cities():
    return jsonify(CITIES)


@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        config.save_settings(request.get_json(silent=True) or {})
    return jsonify(config.public_settings())


# ---------------- сбор ----------------
@app.post("/api/start")
def start():
    data = request.get_json(silent=True) or {}
    cities_, rubrics = split_list(data.get("cities")), split_list(data.get("rubrics"))
    if not cities_ or not rubrics:
        return jsonify(error="Укажите хотя бы один город и одну рубрику."), 400
    with JOB.lock:
        if JOB.running:
            return jsonify(error="Парсер уже запущен."), 409
        JOB.reset()
        JOB.running = True
        JOB.title = f"{cities_[0]}_{rubrics[0]}".lower().replace(" ", "_")
        s = config.load_settings()
        if data.get("limit") not in (None, ""):
            # лимит с формы — на каждую пару город/рубрика
            try:
                s["max_results"] = max(0, int(data["limit"]))
            except (TypeError, ValueError):
                pass
        threading.Thread(target=_run_job, args=(cities_, rubrics, s), daemon=True).start()
    return jsonify(ok=True)


@app.post("/api/stop")
def stop():
    JOB.stop_flag = True
    JOB.log("Запрошена остановка…")
    return jsonify(ok=True)


def _filtered(args):
    flt = F.Filters.from_dict(json.loads(args.get("filters", "{}") or "{}"))
    tab = F.tab_filter(args.get("tab", "all"))
    with JOB.lock:
        recs = list(JOB.records)
    return recs, F.apply(F.apply(recs, tab), flt)


@app.get("/api/status")
def status():
    recs, out = _filtered(request.args)
    page = max(0, int(request.args.get("page", 0)))
    return jsonify(
        running=JOB.running, error=JOB.error, tail=JOB.logs[-1:] or [""],
        total=len(recs), shown=len(out), counters=F.counters(recs),
        rows=out[page * 100:(page + 1) * 100], base=JOB.base,
    )


@app.get("/api/export")
def export_now():
    _, out = _filtered(request.args)
    if not out:
        return jsonify(error="Нет данных для экспорта."), 400
    p = export.save_xlsx(out, config.DB_DIR, f"{JOB.title}_{request.args.get('tab', 'all')}")
    return send_file(p, as_attachment=True, download_name=p.name)


# ---------------- журнал ----------------
@app.get("/api/logs")
def logs():
    return jsonify(lines=JOB.logs[-300:])


@app.post("/api/logs/clear")
def logs_clear():
    with JOB.lock:
        JOB.logs = []
    return jsonify(ok=True)


@app.get("/api/logs/file")
def logs_file():
    if not config.LOG_FILE.exists():
        return Response("", mimetype="text/plain")
    return send_file(config.LOG_FILE, as_attachment=True, download_name="neo.log")


# ---------------- базы ----------------
_cache = {}


def _base_info(p):
    stat = p.stat()
    key = (str(p.resolve()), stat.st_mtime_ns, stat.st_size)
    if key not in _cache:
        recs = export.load_base(p)
        _cache[key] = {
            "count": len(recs), "ready": sum(1 for r in recs if r.get("phones")),
            "no_site": sum(1 for r in recs if not r.get("site")),
            "vk": sum(1 for r in recs if r.get("vk")),
            "tg": sum(1 for r in recs if r.get("tg")),
            "wa": sum(1 for r in recs if r.get("wa")),
        }
    return _cache[key]


def _safe_base(name):
    p = (config.DB_DIR / name).resolve()
    if p.parent != config.DB_DIR.resolve() or p.suffix != ".xlsx" or not p.exists():
        abort(404)
    return p


@app.get("/api/overview")
def overview():
    sent = outreach.load_sent(config.SENT_FILE)
    bases = []
    for b in export.list_bases(config.DB_DIR):
        p = config.DB_DIR / b["name"]
        try:
            info = _base_info(p)
        except Exception:
            info = {"count": 0, "ready": 0, "no_site": 0, "vk": 0, "tg": 0, "wa": 0}
        bases.append({**b, **info, "mockups": mockups.count(config.SITES_DIR, p.stem), "sent": len(sent.get(b["name"], []))})
    return jsonify(
        bases=bases,
        totals={
            "bases": len(bases),
            "orgs": sum(b["count"] for b in bases),
            "mockups": sum(b["mockups"] for b in bases),
            "sent": sum(b["sent"] for b in bases),
        },
    )


@app.post("/api/bases/<name>/open")
def open_base(name):
    p = _safe_base(name)
    with JOB.lock:
        if JOB.running:
            return jsonify(error="Дождитесь окончания сбора."), 409
        JOB.records, JOB.title, JOB.base = export.load_base(p), p.stem, p.name
    return jsonify(ok=True, count=len(JOB.records))


@app.delete("/api/bases/<name>")
def delete_base(name):
    p = _safe_base(name)
    p.unlink()
    resolved = str(p.resolve())
    for key in list(_cache):
        if key[0] == resolved:
            _cache.pop(key, None)
    return jsonify(ok=True)


# ---------------- макеты ----------------
@app.post("/api/mockups/generate")
def mockups_generate():
    d = request.get_json(silent=True) or {}
    p = _safe_base(d.get("base", ""))
    res = mockups.generate(export.load_base(p), config.SITES_DIR, p.stem, bool(d.get("overwrite")))
    JOB.log(f"Макеты: создано {res['made']}, пропущено {res['skipped']} → {res['folder']}")
    return jsonify(res)


@app.get("/api/mockups/zip")
def mockups_zip():
    p = _safe_base(request.args.get("base", ""))
    if not mockups.count(config.SITES_DIR, p.stem):
        return jsonify(error="Для этой базы ещё нет макетов."), 400
    return Response(
        mockups.zip_folder(config.SITES_DIR, p.stem),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={p.stem}_sites.zip"},
    )


# ---------------- рассылка (ручная) и AI ----------------
@app.get("/api/outreach")
def outreach_list():
    p = _safe_base(request.args.get("base", ""))
    ch = request.args.get("channel", "tg")
    if ch not in ("tg", "wa", "vk"):
        abort(400)
    tpl = request.args.get("template") or config.load_settings()["outreach_template"]
    sent = set(outreach.load_sent(config.SENT_FILE).get(p.name, []))
    return jsonify(items=outreach.build(export.load_base(p), ch, tpl, sent))


@app.post("/api/outreach/mark")
def outreach_mark():
    d = request.get_json(silent=True) or {}
    outreach.mark(config.SENT_FILE, _safe_base(d.get("base", "")).name, str(d.get("key", "")), bool(d.get("done", True)))
    return jsonify(ok=True)


@app.post("/api/ai")
def ai_ask():
    prompt = (request.get_json(silent=True) or {}).get("prompt", "").strip()
    if not prompt:
        return jsonify(error="Пустой запрос."), 400
    try:
        return jsonify(text=ai.ask(config.load_settings(), prompt))
    except Exception as e:
        return jsonify(error=str(e)[:300]), 502


@app.get("/api/check-browser")
def check_browser():
    try:
        from playwright.sync_api import sync_playwright
        from core.yandex import ensure_chromium_installed
        ensure_chromium_installed(JOB.log)
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="chromium", headless=True)
            v = b.version
            b.close()
        return jsonify(ok=True, version=v)
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:300])


def main(port=5057):
    url = f"http://127.0.0.1:{port}"
    print(f"{config.APP_NAME} {config.VERSION}: {url}")
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=port, threaded=True), daemon=True).start()
    time.sleep(0.8)
    try:
        # собственное окно (WebView2), иначе — обычный браузер
        import webview
        webview.create_window("Neo parser", url, width=1280, height=860, min_size=(960, 640))
        webview.start()
    except Exception:
        webbrowser.open(url)
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # CI запускает собранный EXE с этим флагом: проверяем загрузку Python DLL
        config.ensure_dirs()
        raise SystemExit(0)
    main()