"""Интеграционный тест парсера на локальном макете Яндекс Карт (нужен Chromium)."""
import sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from flask import Flask
from werkzeug.serving import make_server
from core.yandex import YandexParser
from core import config, filters as F

ORGS = {
    "1": ("Салон Один", "ул. Ленина, 1", "+7 (999) 111-22-33",
          ["https://salon1.ru", "https://vk.com/salon1"]),
    "2": ("Салон Два", "ул. Мира, 2", "8 999 222 33 44", ["https://vk.com/salon2", "https://instagram.com/s2"]),
    "3": ("Салон Три", "ул. Пушкина, 3", "+7 999 333-44-55", ["https://t.me/salon3", "https://wa.me/79993334455"]),
}
mock = Flask("mock")

@mock.get("/maps/")
def lst():
    links = "".join(f'<div class="search-snippet-view"><a href="/maps/org/s{i}/{i}/?x=1">{i}</a></div>'
                    for i in ["1", "2", "3", "1"])           # «1» повторяется — должен быть пропущен
    return f'<html><body><div class="scroll__container" style="height:200px;overflow:auto">{links}</div></body></html>'

@mock.get("/maps/org/<slug>/<oid>/")
def org(slug, oid):
    n, a, ph, links = ORGS[oid]
    ls = "".join(f'<a href="{l}">{l}</a>' for l in links)
    return (f'<html><body><div class="business-card-view"><h1>{n}</h1>'
            f'<a class="business-contacts-view__address-link">{a}</a>'
            f'<div class="orgpage-phones-view__phone-number">{ph}</div>'
            f'<div class="business-rating-badge-view__rating-text">4,{oid}</div>{ls}</div></body></html>')

def test_scraper():
    srv = make_server("127.0.0.1", 5199, mock); threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)
    got, logs = [], []
    s = dict(config.DEFAULTS, headless=True, deep_contact_search=False, geo_grid_search=False,
             delay_min=0.01, delay_max=0.02)
    class P(YandexParser): BASE = "http://127.0.0.1:5199"
    P(s, logs.append, lambda n: None, lambda: False, got.append).run(["Москва"], ["салон"], {"Москва": 13_000_000})
    srv.shutdown()
    by = {r["name"]: r for r in got}
    assert len(got) == 3, (len(got), logs)                       # дубль отсечён
    assert by["Салон Один"]["site"] == "https://salon1.ru" and by["Салон Один"]["vk"] == ["https://vk.com/salon1"]
    assert by["Салон Два"]["site"] == "" and by["Салон Два"]["phones"] == ["+79992223344"]
    assert by["Салон Три"]["tg"] == ["https://t.me/salon3"] and by["Салон Три"]["wa"] == ["https://wa.me/79993334455"]
    assert by["Салон Два"]["rating"] == 4.2
    nos = [r["name"] for r in F.apply(got, F.Filters(no_site=True))]
    assert sorted(nos) == ["Салон Два", "Салон Три"]
    assert [r["name"] for r in F.apply(got, F.Filters(tg=True))] == ["Салон Три"]
    assert [r["name"] for r in F.apply(got, F.Filters(wa=True))] == ["Салон Три"]
    assert sorted(r["name"] for r in F.apply(got, F.Filters(vk=True))) == ["Салон Два", "Салон Один"]

def test_limit_per_pair():
    srv = make_server("127.0.0.1", 5198, mock); threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.3)
    got = []
    s = dict(config.DEFAULTS, headless=True, deep_contact_search=False, geo_grid_search=False, max_results=2, delay_min=0.01, delay_max=0.02, parallel_workers=1)
    class P(YandexParser): BASE = "http://127.0.0.1:5198"
    P(s, lambda m: None, lambda n: None, lambda: False, got.append).run(["Москва"], ["салон"], {})
    srv.shutdown()
    assert len(got) == 2
