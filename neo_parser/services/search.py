"""Orchestrate search across providers and persist results."""

from __future__ import annotations

from typing import Callable, Optional

from ..db import Database
from ..sources.base import CompanyResult
from ..sources.twogis import TwoGisProvider
from .audit import normalize_url
from .scoring import calculate_score


def run_search(
    db: Database,
    query: str,
    city: str,
    *,
    max_pages: int = 3,
    stop_flag: Optional[Callable[[], bool]] = None,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> dict:
    """
    Search 2GIS, save leads, return summary.
    on_progress(message, found, added)
    """
    provider = TwoGisProvider()
    if not provider.is_configured():
        raise RuntimeError(provider.configuration_help())

    found = 0
    added = 0
    errors: list[str] = []

    try:
        for company in provider.search(query, city, max_pages=max_pages, stop_flag=stop_flag):
            if stop_flag and stop_flag():
                break
            found += 1
            lead = _to_lead(company)
            score, reasons, conf = calculate_score(lead)
            lead["score"] = score
            lead["score_reasons"] = reasons
            lead["confidence"] = conf
            if db.add_lead(lead):
                added += 1
            if on_progress:
                on_progress(company.name, found, added)
    except Exception as exc:
        errors.append(str(exc))
        raise

    db.add_history(city, query, found, added, status="stopped" if (stop_flag and stop_flag()) else "done")
    return {"found": found, "added": added, "errors": errors}


def _to_lead(c: CompanyResult) -> dict:
    return {
        "company": c.name,
        "category": c.category,
        "city": c.city,
        "phone": c.phone,
        "email": c.email,
        "website": normalize_url(c.website),
        "vk": c.vk,
        "telegram": c.telegram,
        "address": c.address,
        "source": c.source,
        "source_id": c.source_id,
        "card_url": c.card_url,
        "status": "Новый",
        "notes": "",
    }
