"""Ручная рассылка: готовые ссылки на чаты с подстановкой текста + отметки «отправлено».
Автоматической массовой отправки нет намеренно (риск блокировки аккаунтов и спама)."""
import json, re
from urllib.parse import quote
from pathlib import Path


def load_sent(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def mark(path: Path, base: str, key: str, done=True):
    d = load_sent(path)
    cur = set(d.get(base, []))
    (cur.add if done else cur.discard)(key)
    d[base] = sorted(cur)
    path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def fill(template: str, rec: dict) -> str:
    return (template or "").replace("{name}", rec.get("name", "")).replace("{city}", rec.get("city", ""))


def build(records, channel: str, template: str, sent: set):
    out = []
    for r in records:
        for u in (r.get(channel) or [])[:1]:
            text = fill(template, r)
            link = u + ("?text=" + quote(text) if channel == "wa" else "")
            out.append({"name": r.get("name"), "link": link, "key": u, "text": text, "done": u in sent})
    return out
