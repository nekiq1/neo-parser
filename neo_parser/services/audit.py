"""Website availability and content heuristics."""

from __future__ import annotations

import re
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url.rstrip("/")


def audit_website(url: str, timeout: int = 10) -> dict[str, Any]:
    """Return structured audit result for a company website."""
    url = normalize_url(url)
    result: dict[str, Any] = {
        "status": "Нет сайта",
        "title": "",
        "has_form": False,
        "https": False,
        "mobile": False,
        "portfolio": False,
        "catalog": False,
        "contacts": False,
        "reachable": False,
        "final_url": "",
    }
    if not url:
        return result

    result["https"] = url.lower().startswith("https://")
    try:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; NeoParser/2.0; +https://github.com/nekiq1/neo-parser)"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            final = response.geturl() or url
            result["final_url"] = final
            result["https"] = final.lower().startswith("https://")
            content_type = response.headers.get("Content-Type", "")
            body_bytes = response.read(450_000)
            body = ""
            if "text" in content_type or "html" in content_type or not content_type:
                body = body_bytes.decode("utf-8", "ignore")
            result["status"] = f"HTTP {status}"
            result["reachable"] = 200 <= status < 400
            if body:
                _analyze_html(body, result)
    except HTTPError as error:
        result["status"] = f"HTTP {error.code}"
        result["reachable"] = False
    except (URLError, socket.timeout, TimeoutError, ValueError, OSError):
        result["status"] = "Недоступен"
        result["reachable"] = False
    return result


def _analyze_html(body: str, result: dict[str, Any]) -> None:
    soup = BeautifulSoup(body, "html.parser")
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        result["title"] = re.sub(r"\s+", " ", title_tag.string).strip()[:160]

    # Forms / CTA
    forms = soup.find_all("form")
    inputs = soup.find_all("input", attrs={"type": re.compile(r"tel|email|text", re.I)})
    textareas = soup.find_all("textarea")
    result["has_form"] = bool(forms or (inputs and textareas) or soup.find(string=re.compile(
        r"оставить заявк|заказать звонок|обратн\w+ связь|get a quote|request a call", re.I
    )))

    lower = body.lower()
    # Portfolio / works
    portfolio_kw = (
        "портфолио", "наши работы", "gallery", "portfolio", "проекты",
        "наши проекты", "реализованные", "кейсы", "cases"
    )
    result["portfolio"] = any(k in lower for k in portfolio_kw)

    # Catalog / services
    catalog_kw = (
        "каталог", "услуги", "прайс", "цены", "services", "catalog",
        "наш ассортимент", "продукция", "товары"
    )
    result["catalog"] = any(k in lower for k in catalog_kw)

    # Contact buttons / links
    contact_kw = (
        "whatsapp", "telegram", "viber", "callto:", "tel:",
        "напишите нам", "связаться", "контакты"
    )
    result["contacts"] = any(k in lower for k in contact_kw) or bool(
        soup.find("a", href=re.compile(r"^(tel:|mailto:|https?://wa\.me|https?://t\.me)", re.I))
    )

    # Mobile viewport heuristic
    viewport = soup.find("meta", attrs={"name": re.compile(r"viewport", re.I)})
    result["mobile"] = bool(viewport)
