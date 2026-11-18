"""2GIS search without developer API key.

Same approach as parser-2gis / parser-2gis-new:
  open the public 2gis.ru search pages in Chromium,
  intercept catalog.api.2gis.* JSON responses that the site itself loads.

Requires: playwright + chromium
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import quote

from ..config import APP_DIR
from .base import CompanyResult, SourceProvider

logger = logging.getLogger(__name__)

BROWSER_DIR = APP_DIR / "playwright-browsers"
NAVIGATION_ATTEMPTS = 3

# Public site paths (not official region_id API)
CITY_SLUGS = {
    "Москва": "moscow",
    "Московская область": "moscow",
    "Санкт-Петербург": "spb",
    "Ленинградская область": "spb",
}

# Responses we care about (site catalog, not ads)
ITEM_URL_RE = re.compile(
    r"https://catalog\.api\.2gis\.[^/]+/.*/items",
    re.I,
)


class TwoGisWebProvider(SourceProvider):
    """Browser-based 2GIS collector — no platform.2gis.ru key."""

    name = "2GIS Web"

    def is_configured(self) -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    def configuration_help(self) -> str:
        return (
            "Для поиска без API-ключа нужен Chromium (как в parser-2gis):\n\n"
            "  pip install playwright\n"
            "  playwright install chromium\n\n"
            "Дальше поиск идёт через сайт 2gis.ru: браузер открывает выдачу,\n"
            "приложение перехватывает JSON catalog.api.2gis (ключ разработчика не нужен)."
        )

    @staticmethod
    def _prepare_browser_environment() -> dict[str, str]:
        """Use a persistent per-user browser directory, not PyInstaller's temp folder."""
        BROWSER_DIR.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_DIR)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_DIR)
        return env

    def _ensure_chromium(self) -> None:
        """Install Chromium once into the persistent app directory if absent.

        Playwright's bundled CLI is used so this also works in PyInstaller one-file
        builds, where ``python -m playwright`` would point at the frozen executable.
        """
        env = self._prepare_browser_environment()
        marker = BROWSER_DIR / ".chromium-install-ok"
        if marker.exists():
            return

        try:
            from playwright._impl._driver import compute_driver_executable
            driver_executable, driver_cli = compute_driver_executable()
            command = [str(driver_executable), str(driver_cli), "install", "chromium"]
            logger.info("Installing Playwright Chromium into %s", BROWSER_DIR)
            result = subprocess.run(
                command, env=env, capture_output=True, text=True,
                timeout=900, check=False,
            )
            if result.returncode != 0:
                details = (result.stderr or result.stdout or "").strip()[-4000:]
                raise RuntimeError(
                    "Не удалось установить Chromium для поиска 2ГИС. "
                    "Проверьте подключение к интернету и повторите попытку. " + details
                )
            marker.write_text("ok", encoding="utf-8")
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Установка Chromium заняла слишком много времени. "
                "Проверьте интернет и повторите поиск."
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Не удалось подготовить Chromium: {exc}") from exc

    def search(
        self,
        query: str,
        city: str,
        *,
        max_pages: int = 3,
        stop_flag: Optional[callable] = None,
        filters: Optional[dict] = None,
    ) -> Iterator[CompanyResult]:
        if not self.is_configured():
            raise RuntimeError(self.configuration_help())

        self._ensure_chromium()
        self._prepare_browser_environment()
        from playwright.sync_api import sync_playwright

        slug = CITY_SLUGS.get(city)
        if not slug:
            raise ValueError(f"Нет slug для города: {city}")

        filters = filters or {}
        collected: dict[str, CompanyResult] = {}
        raw_bags: list[dict] = []

        def on_response(response) -> None:
            try:
                url = response.url or ""
                if not ITEM_URL_RE.search(url):
                    return
                if "ads" in url:
                    return
                if response.status != 200:
                    return
                ctype = (response.headers or {}).get("content-type", "")
                if "json" not in ctype and "javascript" not in ctype:
                    # still try
                    pass
                data = response.json()
                if isinstance(data, dict):
                    raw_bags.append(data)
            except Exception:
                return

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--window-size=1365,900",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1365, "height": 900},
                locale="ru-RU",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.on("response", on_response)

            for page_no in range(1, max(1, max_pages) + 1):
                if stop_flag and stop_flag():
                    break
                if page_no == 1:
                    url = f"https://2gis.ru/{slug}/search/{quote(query)}"
                else:
                    url = f"https://2gis.ru/{slug}/search/{quote(query)}/page/{page_no}"
                logger.info("2GIS web open %s", url)
                loaded = False
                for attempt in range(1, NAVIGATION_ATTEMPTS + 1):
                    if stop_flag and stop_flag():
                        break
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                        page.wait_for_timeout(3500)
                        page.mouse.wheel(0, 2400)
                        page.wait_for_timeout(1500)
                        loaded = True
                        break
                    except Exception as exc:
                        logger.warning("page load attempt %s failed: %s", attempt, exc)
                        if attempt < NAVIGATION_ATTEMPTS:
                            time.sleep(attempt * 2)
                if not loaded:
                    continue

                # Parse whatever responses we got so far
                for bag in raw_bags:
                    for item in _extract_items(bag):
                        company = _item_to_company(item, city)
                        if not company or not company.name:
                            continue
                        if not _pass_filters(company, filters):
                            continue
                        key = company.source_id or f"{company.name}|{company.phone}|{company.address}"
                        if key not in collected:
                            collected[key] = company
                raw_bags.clear()

                if stop_flag and stop_flag():
                    break

            browser.close()

        for company in collected.values():
            yield company


def _extract_items(data: dict) -> list[dict]:
    """Pull firm/branch objects from various catalog payloads."""
    items: list[dict] = []
    result = data.get("result")
    if isinstance(result, dict):
        chunk = result.get("items")
        if isinstance(chunk, list):
            items.extend([x for x in chunk if isinstance(x, dict)])
    # byid sometimes nests differently
    if not items and isinstance(data.get("items"), list):
        items.extend([x for x in data["items"] if isinstance(x, dict)])
    return items


def _item_to_company(item: dict, city: str) -> CompanyResult | None:
    # skip non-org geometry noise
    itype = (item.get("type") or "").lower()
    if itype and itype not in ("branch", "org", "firm", ""):
        # still allow if has name + contacts
        if not item.get("name") and not (item.get("name_ex") or {}).get("primary"):
            return None

    name = (
        item.get("name")
        or (item.get("name_ex") or {}).get("primary")
        or item.get("full_name")
        or ""
    )
    name = str(name).strip()
    if not name:
        return None

    address = item.get("full_address_name") or item.get("address_name") or ""
    if not address:
        addr = item.get("address") or {}
        if isinstance(addr, dict):
            parts = [addr.get("postcode"), addr.get("city_name") or addr.get("city"),
                     addr.get("street"), addr.get("number")]
            address = ", ".join(p for p in parts if p)

    rubrics = item.get("rubrics") or []
    category = ""
    if isinstance(rubrics, list) and rubrics:
        category = (rubrics[0].get("name") if isinstance(rubrics[0], dict) else "") or ""

    phone = email = website = vk = telegram = whatsapp = ""
    for group in item.get("contact_groups") or []:
        if not isinstance(group, dict):
            continue
        for contact in group.get("contacts") or []:
            if not isinstance(contact, dict):
                continue
            ctype = (contact.get("type") or "").lower()
            value = contact.get("value") or contact.get("text") or contact.get("url") or ""
            if not value:
                continue
            if ctype in ("phone", "phone_additional") and not phone:
                phone = str(value)
            elif ctype == "email" and not email:
                email = str(value)
            elif ctype in ("website", "site") and not website:
                website = str(value)
            elif ctype in ("vkontakte", "vk") and not vk:
                vk = str(value)
            elif ctype == "telegram" and not telegram:
                telegram = str(value)
            elif ctype in ("whatsapp", "whats_app", "wa") and not whatsapp:
                whatsapp = str(value)

    links = item.get("links") or {}
    if isinstance(links, dict):
        if not website:
            site = links.get("website") or links.get("site")
            if isinstance(site, list) and site:
                website = site[0].get("url") or site[0].get("value") or ""
            elif isinstance(site, dict):
                website = site.get("url") or ""
        vk = vk or links.get("vkontakte") or links.get("vk") or ""
        telegram = telegram or links.get("telegram") or ""
        whatsapp = whatsapp or links.get("whatsapp") or links.get("wa") or ""

    source_id = str(item.get("id") or "")
    # strip hash suffix if present
    source_id = source_id.split("_")[0]
    card_url = f"https://2gis.ru/firm/{source_id}" if source_id else ""

    return CompanyResult(
        name=name,
        phone=phone.strip(),
        email=email.strip(),
        address=str(address).strip(),
        city=city,
        category=str(category).strip(),
        website=website.strip(),
        vk=vk.strip(),
        telegram=telegram.strip(),
        whatsapp=whatsapp.strip(),
        source="2GIS Web",
        source_id=source_id,
        card_url=card_url,
        raw=item,
    )


def _pass_filters(c: CompanyResult, filters: dict) -> bool:
    """Post-filters: only_with_phone, only_without_website, only_with_website, only_with_email."""
    if filters.get("require_public_contact") and not any(
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
