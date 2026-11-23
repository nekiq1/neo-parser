import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import contacts as C, filters as F, export

RECS = [
    {"name": "A", "site": "http://a.ru", "vk": ["https://vk.com/a"], "tg": [], "wa": [], "phones": ["+79990000001"], "rating": 4.8},
    {"name": "B", "site": "", "vk": [], "tg": ["https://t.me/b"], "wa": ["https://wa.me/79990000002"], "phones": ["+79990000002"], "rating": 4.1},
    {"name": "C", "site": "", "vk": ["https://vk.com/c"], "tg": [], "wa": [], "phones": [], "rating": 3.0},
    {"name": "D", "site": "", "vk": [], "tg": [], "wa": [], "phones": ["+79990000004"]},
]
names = lambda f: [r["name"] for r in F.apply(RECS, f)]

def test_no_site():            assert names(F.Filters(no_site=True)) == ["B", "C", "D"]
def test_has_site():           assert names(F.Filters(has_site=True)) == ["A"]
def test_vk_only():            assert names(F.Filters(vk=True)) == ["A", "C"]
def test_tg_only():            assert names(F.Filters(tg=True)) == ["B"]
def test_wa_only():            assert names(F.Filters(wa=True)) == ["B"]
def test_any_vs_all():
    assert names(F.Filters(tg=True, vk=True)) == ["A", "B", "C"]
    assert names(F.Filters(tg=True, wa=True, messengers_mode="all")) == ["B"]
def test_no_site_and_vk():     assert names(F.Filters(no_site=True, vk=True)) == ["C"]
def test_no_messengers():      assert names(F.Filters(only_no_messengers=True)) == ["D"]
def test_rating_phone():
    assert names(F.Filters(min_rating=4.0)) == ["A", "B"]
    assert names(F.Filters(has_phone=True)) == ["A", "B", "D"]
def test_counters():           assert F.counters(RECS) == {"all": 4, "no_site": 3, "vk": 2, "tg": 1, "wa": 1}
def test_from_dict_conflict(): assert F.Filters.from_dict({"no_site": 1, "has_site": 1}).has_site is False
def test_tabs():               assert [r["name"] for r in F.apply(RECS, F.tab_filter("no_site"))] == ["B", "C", "D"]

def test_site_normalisation():
    assert C.normalize_site("vk.com/shop") == ""
    assert C.normalize_site("https://yandex.ru/maps") == ""
    assert C.normalize_site("shop.ru").startswith("http")
    assert C.normalize_site("t.me/x") == ""
def test_extract():
    r = C.extract_from_text('<a href="https://t.me/shop_bot">x</a> https://wa.me/+79991234567 '
                            'https://api.whatsapp.com/send?phone=79990001122 https://vk.com/club1 a@b.ru x@y.png')
    assert r["tg"] == ["https://t.me/shop_bot"] and r["vk"] == ["https://vk.com/club1"]
    assert r["wa"] == ["https://wa.me/79991234567", "https://wa.me/79990001122"] and r["email"] == ["a@b.ru"]
def test_tg_share_ignored():    assert C.extract_from_text("https://t.me/share/url?u=1")["tg"] == []
def test_phone():               assert C.normalize_phone("8 (999) 123-45-67") == "+79991234567"
def test_classify():
    r = C.classify_links(["https://vk.com/x", "https://my-shop.ru/", "https://t.me/y"])
    assert r["site"] == "https://my-shop.ru/" and r["vk"] and r["tg"]
def test_only_socials_means_no_site():
    assert C.classify_links(["https://vk.com/x", "https://instagram.com/y"])["site"] == ""

def test_xlsx_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        p = export.save_xlsx(RECS, Path(d), "тест")
        back = export.load_base(p)
        assert len(back) == 4 and back[1]["tg"] == ["https://t.me/b"] and back[0]["name"] == "A"
        # On Windows the XLSX must be immediately releasable after reading.
        p.unlink()
