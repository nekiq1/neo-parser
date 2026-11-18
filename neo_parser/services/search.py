"""Orchestrate search across providers and persist results."""

from __future__ import annotations

from typing import Callable, Optional

from ..db import Database
from ..config import AUDIT_TIMEOUT
from ..sources.base import CompanyResult
from ..sources.twogis import TwoGisProvider
from ..sources.twogis_web import TwoGisWebProvider
from .audit import audit_website, normalize_url
from .scoring import calculate_score


def run_search(
    db: Database,
    query: str,
    city: str,
    *,
    max_pages: int = 3,
    stop_flag: Optional[Callable[[], bool]] = None,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
    filters: Optional[dict] = None,
) -> dict:
    """
    Search 2GIS without requiring a developer key when Playwright is available.
    Fallback: official API if TWOGIS_API_KEY is set.
    """
    filters = filters or {}
    provider = _pick_provider()
    found = 0
    added = 0
    errors: list[str] = []

    try:
        kwargs = dict(max_pages=max_pages, stop_flag=stop_flag)
        # web provider accepts filters
        if isinstance(provider, TwoGisWebProvider):
            kwargs["filters"] = filters
        for company in provider.search(query, city, **kwargs):
            if stop_flag and stop_flag():
                break
            if not _pass_filters(company, filters):
                continue
            found += 1
            lead = _to_lead(company)
            # Every discovered website is checked before the lead is scored.
            audit = audit_website(lead["website"], timeout=AUDIT_TIMEOUT)
            score, reasons, conf = calculate_score(lead, audit)
            lead.update({
                "score": score,
                "score_reasons": reasons,
                "confidence": conf,
                "website_status": audit.get("status", ""),
                "website_title": audit.get("title", ""),
                "website_has_form": audit.get("has_form", False),
                "website_https": audit.get("https", False),
                "website_mobile": audit.get("mobile", False),
                "website_portfolio": audit.get("portfolio", False),
                "website_catalog": audit.get("catalog", False),
                "website_contacts": audit.get("contacts", False),
            })
            if db.add_lead(lead):
                added += 1
            if on_progress:
                on_progress(company.name, found, added)
    except Exception as exc:
        errors.append(str(exc))
        raise

    status = "stopped" if (stop_flag and stop_flag()) else "done"
    db.add_history(city, query, found, added, status=status)
    return {
        "found": found,
        "added": added,
        "errors": errors,
        "provider": getattr(provider, "name", type(provider).__name__),
    }


def _pick_provider():
    web = TwoGisWebProvider()
    if web.is_configured():
        return web
    api = TwoGisProvider()
    if api.is_configured():
        return api
    # Prefer clear install instructions for browser path
    raise RuntimeError(web.configuration_help())


def _pass_filters(c: CompanyResult, filters: dict) -> bool:
    if filters.get("require_public_contact", True) and not any(
        (c.phone, c.email, c.website, c.vk, c.telegram, c.whatsapp)
    ):
        return False
    if filters.get("only_with_phone") and not c.phone:
        return False
    if filters.get("only_with_email") and not c.email:
        return False
    if filters.get("only_with_website") and not c.website:
        return False
    if filters.get("only_without_website") and c.website:
        return False
    return True


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
        "whatsapp": c.whatsapp,
        "address": c.address,
        "source": c.source,
        "source_id": c.source_id,
        "card_url": c.card_url,
        "status": "Новый",
        "notes": "",
    }
