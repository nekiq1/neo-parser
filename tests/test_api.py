import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import config, export
import app as A

def _sandbox():
    d = Path(tempfile.mkdtemp())
    config.DB_DIR, config.SITES_DIR, config.LOG_DIR = d / "databases", d / "websites", d / "logs"
    config.SETTINGS_FILE, config.SENT_FILE, config.LOG_FILE = d / "settings.json", d / "sent.json", d / "logs" / "neo.log"
    config.ensure_dirs()
    # Tests share the Flask app module; reset global state between test cases.
    A.JOB.reset()
    with A.JOB.lock:
        A.JOB.logs = []
    A._cache.clear()

RECS = [{"name": "X", "category": "c", "city": "Москва", "site": "", "vk": ["https://vk.com/x"], "tg": [], "wa": [], "phones": ["+79990000001"]},
        {"name": "Y", "site": "http://y.ru", "vk": [], "tg": ["https://t.me/y"], "wa": ["https://wa.me/79990000002"], "phones": []}]

def test_api():
    _sandbox(); c = A.app.test_client()
    assert c.get("/").status_code == 200 and len(c.get("/api/cities").json) > 1000
    assert c.post("/api/start", json={"cities": "", "rubrics": ""}).status_code == 400
    A.JOB.records = list(RECS)
    q = lambda tab, f="{}": c.get("/api/status", query_string={"tab": tab, "filters": f}).json
    assert q("all")["total"] == 2 and q("no_site")["shown"] == 1 and q("tg")["rows"][0]["name"] == "Y"
    assert q("vk", json.dumps({"no_site": True}))["shown"] == 1
    assert q("all", json.dumps({"no_site": True, "tg": True}))["shown"] == 0
    assert c.get("/api/export", query_string={"tab": "vk", "filters": "{}"}).data[:2] == b"PK"
    s = c.post("/api/settings", json={"parallel_workers": 99, "max_results": "abc", "deepseek_api_key": "sk-secret"}).json
    assert s["parallel_workers"] == 8 and s["max_results"] == 0
    assert s["deepseek_api_key"] == "" and s["deepseek_api_key_set"] is True      # секрет не уходит в UI
    c.post("/api/settings", json={"deepseek_api_key": ""})                         # пустое поле ключ не стирает
    assert config.load_settings()["deepseek_api_key"] == "sk-secret"

def test_bases_mockups_outreach_logs():
    _sandbox(); c = A.app.test_client()
    p = export.save_xlsx(RECS, config.DB_DIR, "leads_test"); n = p.name
    ov = c.get("/api/overview").json
    b = ov["bases"][0]
    assert ov["totals"]["bases"] == 1 and b["count"] == 2 and b["ready"] == 1 and b["no_site"] == 1 and b["tg"] == 1
    r = c.post("/api/mockups/generate", json={"base": n}).json
    assert r["made"] == 2 and c.post("/api/mockups/generate", json={"base": n}).json["skipped"] == 2
    assert c.post("/api/mockups/generate", json={"base": n, "overwrite": True}).json["made"] == 2
    assert c.get("/api/overview").json["bases"][0]["mockups"] == 2
    assert c.get("/api/mockups/zip", query_string={"base": n}).data[:2] == b"PK"
    items = c.get("/api/outreach", query_string={"base": n, "channel": "wa", "template": "Привет, {name}!"}).json["items"]
    assert items[0]["link"].startswith("https://wa.me/79990000002?text=") and "%D0%9F" in items[0]["link"]
    c.post("/api/outreach/mark", json={"base": n, "key": items[0]["key"], "done": True})
    assert c.get("/api/overview").json["bases"][0]["sent"] == 1
    assert c.get("/api/outreach", query_string={"base": n, "channel": "tg"}).json["items"][0]["done"] is False
    assert c.get("/api/outreach", query_string={"base": n, "channel": "xx"}).status_code == 400
    assert c.post(f"/api/bases/{n}/open").json["count"] == 2
    A.JOB.log("тест"); assert "тест" in c.get("/api/logs").json["lines"][-1]
    c.post("/api/logs/clear"); assert c.get("/api/logs").json["lines"] == []
    assert c.get("/api/logs/file").status_code == 200
    assert c.delete("/api/bases/..%2Fx.xlsx").status_code == 404
    assert c.delete(f"/api/bases/{n}").status_code == 200 and c.get("/api/overview").json["totals"]["bases"] == 0
    assert c.post("/api/ai", json={"prompt": "hi"}).status_code == 502      # без ключа — внятная ошибка
