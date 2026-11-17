"""Official 2GIS Catalog API provider.

Docs: https://docs.2gis.com/en/api/search/places/overview
Uses /3.0/items endpoint. Requires a valid API key from platform.2gis.ru.
"""

from __future__ import annotations

import logging
from typing import Iterator, Optional
from urllib.parse import quote

import httpx

from ..config import CITIES, TWOGIS_BASE, TWOGIS_MAX_PAGES, get_api_key
from .base import CompanyResult, SourceProvider

logger = logging.getLogger(__name__)


class TwoGisProvider(SourceProvider):
    name = "2GIS"

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or get_api_key()).strip()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def configuration_help(self) -> str:
        return (
            "Для поиска компаний через 2ГИС нужен API-ключ.\n\n"
            "1. Зарегистрируйтесь на https://platform.2gis.ru или https://dev.2gis.ru\n"
            "2. Создайте ключ с доступом к Catalog / Places API\n"
            "3. Вставьте ключ в разделе «Настройки» приложения\n"
            "   или задайте переменную окружения TWOGIS_API_KEY\n\n"
            "Без ключа поиск недоступен — приложение не имитирует данные."
        )

    def search(
        self,
        query: str,
        city: str,
        *,
        max_pages: int | None = None,
        stop_flag: Optional[callable] = None,
    ) -> Iterator[CompanyResult]:
        if not self.is_configured():
            raise RuntimeError(self.configuration_help())

        city_info = CITIES.get(city)
        if not city_info:
            raise ValueError(f"Неизвестный город: {city}. Доступны: {', '.join(CITIES)}")

        region_id = city_info["region_id"]
        center = city_info["center"]
        pages = max_pages or TWOGIS_MAX_PAGES
        page = 1
        seen_ids: set[str] = set()

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            while page <= pages:
                if stop_flag and stop_flag():
                    break

                params = {
                    "q": query,
                    "type": "branch",
                    "region_id": region_id,
                    "page": page,
                    "page_size": 50,
                    "locale": "ru_RU",
                    "fields": (
                        "items.point,items.full_address_name,items.address,"
                        "items.rubrics,items.org,items.contact_groups,"
                        "items.schedule,items.links,items.name_ex"
                    ),
                    "key": self.api_key,
                }
                # Prefer sort near city center
                if center:
                    params["sort_point"] = center
                    params["location"] = center

                url = f"{TWOGIS_BASE}/3.0/items"
                try:
                    resp = client.get(url, params=params)
                except httpx.HTTPError as exc:
                    logger.error("2GIS request failed: %s", exc)
                    raise RuntimeError(f"Ошибка сети при запросе к 2ГИС: {exc}") from exc

                if resp.status_code == 403:
                    raise RuntimeError(
                        "Ключ 2ГИС отклонён (403). Проверьте права доступа к Catalog API "
                        "и лимиты на platform.2gis.ru."
                    )
                if resp.status_code == 401:
                    raise RuntimeError("Неверный API-ключ 2ГИС (401).")
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"2ГИС вернул HTTP {resp.status_code}: {resp.text[:300]}"
                    )

                data = resp.json()
                meta_code = data.get("meta", {}).get("code")
                if meta_code and meta_code != 200:
                    raise RuntimeError(
                        f"2ГИС meta.code={meta_code}: {data.get('meta')}"
                    )

                items = data.get("result", {}).get("items") or []
                if not items:
                    break

                for item in items:
                    if stop_flag and stop_flag():
                        return
                    cid = str(item.get("id") or "")
                    if cid and cid in seen_ids:
                        continue
                    if cid:
                        seen_ids.add(cid)
                    result = self._parse_item(item, city)
                    if result and result.name:
                        yield result

                total = data.get("result", {}).get("total", 0)
                if page * 50 >= total:
                    break
                page += 1

    def _parse_item(self, item: dict, city: str) -> CompanyResult | None:
        name = (
            item.get("name")
            or (item.get("name_ex") or {}).get("primary")
            or item.get("full_name")
            or ""
        )
        if not name:
            return None

        address = item.get("full_address_name") or ""
        if not address:
            addr = item.get("address") or {}
            parts = [
                addr.get("postcode"),
                addr.get("city_name") or addr.get("city"),
                addr.get("street"),
                addr.get("number"),
            ]
            address = ", ".join(p for p in parts if p)

        rubrics = item.get("rubrics") or []
        category = ""
        if rubrics:
            category = rubrics[0].get("name") or ""

        phone = ""
        email = ""
        website = ""
        vk = ""
        telegram = ""

        for group in item.get("contact_groups") or []:
            for contact in group.get("contacts") or []:
                ctype = (contact.get("type") or "").lower()
                value = contact.get("value") or contact.get("text") or ""
                if not value:
                    continue
                if ctype in ("phone", "phone_additional") and not phone:
                    phone = value
                elif ctype == "email" and not email:
                    email = value
                elif ctype in ("website", "site") and not website:
                    website = value
                elif ctype == "vkontakte" and not vk:
                    vk = value
                elif ctype == "telegram" and not telegram:
                    telegram = value

        # links fallback
        links = item.get("links") or {}
        if not website and links.get("website"):
            site_list = links["website"]
            if isinstance(site_list, list) and site_list:
                website = site_list[0].get("url") or site_list[0].get("value") or ""
            elif isinstance(site_list, dict):
                website = site_list.get("url") or ""

        source_id = str(item.get("id") or "")
        card_url = ""
        if source_id:
            # Public 2GIS card URL pattern
            card_url = f"https://2gis.ru/firm/{source_id}"

        return CompanyResult(
            name=name.strip(),
            phone=phone.strip(),
            email=email.strip(),
            address=address.strip(),
            city=city,
            category=category.strip(),
            website=website.strip(),
            vk=vk.strip(),
            telegram=telegram.strip(),
            source="2GIS",
            source_id=source_id,
            card_url=card_url,
            raw=item,
        )
