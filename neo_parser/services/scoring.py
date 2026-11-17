"""Explainable lead score 0–100."""

from __future__ import annotations

from typing import Any


def calculate_score(
    lead: dict[str, Any],
    audit: dict[str, Any] | None = None,
) -> tuple[int, list[str], int]:
    """
    Returns (score, reasons, confidence).

    Higher score = more likely needs a website / improvement.
    Absence of a site is NOT treated as guaranteed purchase intent.
    """
    audit = audit or {}
    score = 0
    reasons: list[str] = []
    confidence = 55

    website = (lead.get("website") or "").strip()
    status = audit.get("status") or lead.get("website_status") or ""
    has_form = bool(audit.get("has_form") if "has_form" in audit else lead.get("website_has_form"))
    reachable = audit.get("reachable")
    https = audit.get("https", True)
    portfolio = audit.get("portfolio", False)
    catalog = audit.get("catalog", False)
    contacts = audit.get("contacts", False)
    mobile = audit.get("mobile", True)

    # Website presence / health
    if not website:
        score += 30
        reasons.append("Нет указанного сайта (+30)")
        confidence = 45  # lower confidence — field may be empty in directory
    else:
        if status.startswith("Недоступен") or reachable is False:
            score += 22
            reasons.append("Сайт недоступен (+22)")
            confidence = 70
        elif status.startswith("HTTP 4") or status.startswith("HTTP 5"):
            score += 18
            reasons.append(f"Сайт отвечает ошибкой {status} (+18)")
            confidence = 65
        else:
            if not https:
                score += 8
                reasons.append("Нет HTTPS (+8)")
            if not mobile:
                score += 6
                reasons.append("Нет viewport / мобильной адаптации (+6)")
            if not portfolio:
                score += 7
                reasons.append("Не найдено портфолио (+7)")
            if not catalog:
                score += 5
                reasons.append("Не найден каталог/услуги (+5)")
            if not has_form:
                score += 10
                reasons.append("Нет формы заявки (+10)")
            if not contacts:
                score += 5
                reasons.append("Слабые кнопки связи (+5)")
            if reachable:
                confidence = 75

    # Business signals (increase score slightly — active business is addressable)
    if lead.get("phone"):
        score += 8
        reasons.append("Есть телефон (+8)")
    if lead.get("email"):
        score += 5
        reasons.append("Есть email (+5)")
    if lead.get("vk") or lead.get("telegram"):
        score += 4
        reasons.append("Есть соцсети (+4)")
    if lead.get("address"):
        score += 3
        reasons.append("Есть адрес (+3)")
    if lead.get("category"):
        score += 2
        reasons.append("Есть категория (+2)")

    # Cap
    score = max(0, min(100, score))
    confidence = max(20, min(95, confidence))
    if not reasons:
        reasons.append("Недостаточно данных для детальной оценки")
    return score, reasons, confidence
