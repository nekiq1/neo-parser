"""Фильтры результатов Neo parser.

Новые функции относительно базовой версии:
  1) no_site — только компании без сайта;
  2) vk / tg / wa — поиск по каждому мессенджеру отдельно (или комбинацией).
"""
from dataclasses import dataclass


@dataclass
class Filters:
    no_site: bool = False
    has_site: bool = False
    vk: bool = False
    tg: bool = False
    wa: bool = False
    messengers_mode: str = "any"   # any — хотя бы один из выбранных; all — все выбранные
    has_phone: bool = False
    has_email: bool = False
    min_rating: float = 0.0
    only_no_messengers: bool = False

    @classmethod
    def from_dict(cls, d):
        d = d or {}
        f = cls()
        for k in ("no_site", "has_site", "vk", "tg", "wa", "has_phone", "has_email", "only_no_messengers"):
            setattr(f, k, bool(d.get(k)))
        f.messengers_mode = "all" if d.get("messengers_mode") == "all" else "any"
        try:
            f.min_rating = float(d.get("min_rating") or 0)
        except (TypeError, ValueError):
            f.min_rating = 0.0
        if f.no_site and f.has_site:      # взаимоисключающие — приоритет у «без сайта»
            f.has_site = False
        return f


def match(rec: dict, f: Filters) -> bool:
    if f.no_site and rec.get("site"):
        return False
    if f.has_site and not rec.get("site"):
        return False
    if f.has_phone and not rec.get("phones"):
        return False
    if f.has_email and not rec.get("email"):
        return False
    if f.min_rating and (rec.get("rating") or 0) < f.min_rating:
        return False
    if f.only_no_messengers and any(rec.get(k) for k in ("vk", "tg", "wa")):
        return False
    wanted = [k for k in ("vk", "tg", "wa") if getattr(f, k)]
    if wanted:
        hits = [bool(rec.get(k)) for k in wanted]
        if not (all(hits) if f.messengers_mode == "all" else any(hits)):
            return False
    return True


def apply(records, f: Filters):
    return [r for r in records if match(r, f)]


def counters(records) -> dict:
    return {
        "all": len(records),
        "no_site": sum(1 for r in records if not r.get("site")),
        "vk": sum(1 for r in records if r.get("vk")),
        "tg": sum(1 for r in records if r.get("tg")),
        "wa": sum(1 for r in records if r.get("wa")),
    }


def tab_filter(tab: str) -> Filters:
    return {
        "no_site": Filters(no_site=True),
        "vk": Filters(vk=True),
        "tg": Filters(tg=True),
        "wa": Filters(wa=True),
    }.get(tab, Filters())
