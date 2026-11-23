"""Шаблонные макеты сайтов по данным компании (без нейросети), сохраняются как HTML."""
import html, re, zipfile, io
from pathlib import Path
from .export import safe_name

TPL = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name}</title><style>
:root{{--a:#19e3ff;--b:#b455ff;--bg:#0b0b12;--tx:#eef}}*{{box-sizing:border-box}}
body{{margin:0;font:16px/1.6 system-ui,sans-serif;background:var(--bg);color:var(--tx)}}
header{{padding:72px 24px;text-align:center;background:radial-gradient(60% 80% at 50% 0,#27104a,transparent)}}
h1{{font-size:clamp(28px,6vw,52px);margin:0 0 8px;background:linear-gradient(90deg,var(--a),var(--b));-webkit-background-clip:text;color:transparent}}
.sub{{color:#9aa;margin:0 0 24px}}.btn{{display:inline-block;margin:6px;padding:12px 22px;border-radius:10px;color:#fff;text-decoration:none;
border:1px solid var(--a);box-shadow:0 0 18px #19e3ff55}}main{{max-width:760px;margin:0 auto;padding:24px}}
.card{{border:1px solid #2a2a3d;border-radius:14px;padding:18px;margin:14px 0;background:#12121c}}small{{color:#889}}</style></head><body>
<header><h1>{name}</h1><p class="sub">{category} · {city}</p>{buttons}</header>
<main><div class="card"><b>Адрес</b><br>{address}</div><div class="card"><b>Контакты</b><br>{contacts}</div>
<div class="card"><b>О компании</b><br>Здесь будет описание услуг, цены и отзывы клиентов. {rating}</div>
<small>Макет создан в Neo parser — заготовка для доработки.</small></main></body></html>"""


def _e(x):
    return html.escape(str(x or ""))


def render(rec: dict) -> str:
    phones = rec.get("phones") or []
    btns = "".join(f'<a class="btn" href="tel:{_e(p)}">{_e(p)}</a>' for p in phones[:2])
    for key, label in (("tg", "Telegram"), ("wa", "WhatsApp"), ("vk", "ВКонтакте")):
        for u in (rec.get(key) or [])[:1]:
            btns += f'<a class="btn" href="{_e(u)}">{label}</a>'
    contacts = "<br>".join(_e(x) for x in phones + (rec.get("email") or [])) or "—"
    rating = f"Рейтинг на Яндекс Картах: {_e(rec['rating'])}." if rec.get("rating") else ""
    return TPL.format(name=_e(rec.get("name")), category=_e(rec.get("category")), city=_e(rec.get("city")),
                      address=_e(rec.get("address")) or "—", buttons=btns, contacts=contacts, rating=rating)


def folder(sites_dir: Path, base_stem: str) -> Path:
    return sites_dir / safe_name(base_stem)


def count(sites_dir: Path, base_stem: str) -> int:
    f = folder(sites_dir, base_stem)
    return len(list(f.glob("*.html"))) if f.exists() else 0


def generate(records, sites_dir: Path, base_stem: str, overwrite=False) -> dict:
    out = folder(sites_dir, base_stem)
    out.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for i, r in enumerate(records, 1):
        p = out / f"{i:04d}_{safe_name(r.get('name') or 'site')[:40]}.html"
        if p.exists() and not overwrite:
            skipped += 1
            continue
        p.write_text(render(r), encoding="utf-8")
        made += 1
    return {"made": made, "skipped": skipped, "folder": str(out)}


def zip_folder(sites_dir: Path, base_stem: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in folder(sites_dir, base_stem).glob("*.html"):
            z.write(p, p.name)
    return buf.getvalue()
