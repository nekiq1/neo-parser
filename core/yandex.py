"""Сбор организаций из Яндекс Карт (Playwright, async).

Селекторы Яндекса меняются, поэтому для каждого поля есть цепочка запасных
вариантов, а контакты дополнительно ищутся по всем ссылкам карточки.
"""
import asyncio
import os
import random
import re
import sys
import subprocess
import threading
from pathlib import Path
from urllib.parse import quote

from .contacts import classify_links, normalize_phone, PHONE_RE, merge
from .deep import scan_site
from .config import ROOT

ORG_HREF = re.compile(r"/maps/org/[^/]+/(\d+)")
DISTRICT_SUFFIX = ["центр", "север", "юг", "запад", "восток"]
_BROWSER_INSTALL_LOCK = threading.Lock()


class StopRequested(Exception):
    pass


class CaptchaError(Exception):
    pass


def _browsers_path():
    """Хранить браузер рядом с приложением, а не внутри временной папки PyInstaller."""
    p = ROOT / "browsers"
    p.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(p))
    return Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"])


def ensure_chromium_installed(log=None):
    """Установить только обычный Chromium при первом запуске (без второго Headless Shell)."""
    with _BROWSER_INSTALL_LOCK:
        browser_root = _browsers_path()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            executable = Path(pw.chromium.executable_path)
        if executable.is_file():
            return executable

        from playwright._impl._driver import compute_driver_executable
        node, cli = compute_driver_executable()
        if not Path(node).is_file() or not Path(cli).is_file():
            raise RuntimeError("Не найден встроенный установщик Playwright. Переустановите Neo parser.")

        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_root)
        if log:
            log("Chromium ещё не установлен. Загружаю браузер (один раз, требуется интернет)…")
        try:
            result = subprocess.run(
                [node, cli, "install", "chromium", "--no-shell"],
                env=env, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=900, check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Загрузка Chromium заняла больше 15 минут. Проверьте интернет и повторите.") from None

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[-1200:]
            raise RuntimeError("Не удалось установить Chromium. Проверьте интернет. " + detail)

        with sync_playwright() as pw:
            executable = Path(pw.chromium.executable_path)
        if not executable.is_file():
            raise RuntimeError("Установщик завершился, но исполняемый файл Chromium не найден.")
        if log:
            log("Chromium установлен. В следующий раз повторная загрузка не потребуется.")
        return executable


def split_list(s) -> list:
    if isinstance(s, list):
        items = s
    else:
        items = re.split(r"[\n;,]+", s or "")
    return [i.strip() for i in items if i and i.strip()]


class YandexParser:
    BASE = "https://yandex.ru"

    def __init__(self, settings, log, progress, is_stopped, on_record):
        self.s = settings
        self.log = log
        self.progress = progress
        self.is_stopped = is_stopped
        self.on_record = on_record
        self.seen = set()
        self.found = 0
        self.pair_found = 0

    # ---------- публичный запуск ----------
    def run(self, cities, rubrics, city_meta=None):
        ensure_chromium_installed(self.log)
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        asyncio.run(self._run(cities, rubrics, city_meta or {}))

    async def _run(self, cities, rubrics, city_meta):
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                channel="chromium",  # headless работает через обычный Chromium; отдельный shell не нужен
                headless=bool(self.s["headless"]),
                args=["--disable-blink-features=AutomationControlled", "--lang=ru-RU"])
            ctx = await browser.new_context(
                locale="ru-RU", viewport={"width": 1366, "height": 850},
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
            try:
                for city in cities:
                    for rubric in rubrics:
                        self.pair_found = 0
                        for query in self._queries(city, rubric, city_meta.get(city, 0)):
                            self._check_stop()
                            if self._limit_reached():
                                break
                            await self._collect_query(ctx, city, rubric, query)
            finally:
                await ctx.close()
                await browser.close()

    # ---------- вспомогательное ----------
    def _queries(self, city, rubric, population):
        base = f"{rubric} {city}"
        qs = [base]
        if self.s.get("geo_grid_search") and population >= 500_000:
            qs += [f"{base} {d}" for d in DISTRICT_SUFFIX]
        return qs

    def _check_stop(self):
        if self.is_stopped():
            raise StopRequested()

    def _limit_reached(self):
        m = int(self.s.get("max_results") or 0)
        return bool(m) and self.pair_found >= m

    async def _pause(self):
        await asyncio.sleep(random.uniform(self.s["delay_min"], self.s["delay_max"]))

    async def _guard_captcha(self, page):
        def blocked():
            return "captcha" in page.url.lower() or bool(re.search(
                r"showcaptcha|CheckboxCaptcha|SmartCaptcha", page.url))
        if not blocked():
            try:
                if await page.locator(".CheckboxCaptcha, .AdvancedCaptcha, #js-button").count() == 0:
                    return
            except Exception:
                return
        if self.s["headless"]:
            raise CaptchaError("Яндекс показал капчу. Выключите фоновый режим в настройках "
                               "и пройдите капчу в окне браузера.")
        self.log("Капча! Пройдите её в окне браузера — жду до 3 минут…")
        for _ in range(90):
            self._check_stop()
            await asyncio.sleep(2)
            if not blocked() and await page.locator(".CheckboxCaptcha, .AdvancedCaptcha").count() == 0:
                self.log("Капча пройдена, продолжаю.")
                return
        raise CaptchaError("Капча не пройдена за 3 минуты.")

    # ---------- сбор списка ----------
    async def _collect_query(self, ctx, city, rubric, query):
        self.log(f"Поиск: «{query}»")
        page = await ctx.new_page()
        try:
            await page.goto(f"{self.BASE}/maps/?text={quote(query)}&z=11",
                            wait_until="domcontentloaded", timeout=60000)
            await self._guard_captcha(page)
            try:
                await page.wait_for_selector('a[href*="/maps/org/"]', timeout=20000)
            except Exception:
                self.log("Нет результатов по запросу.")
                return
            links = await self._scroll_collect(page)
        finally:
            await page.close()

        new = []
        for href in links:
            m = ORG_HREF.search(href)
            if m and m.group(1) not in self.seen:
                self.seen.add(m.group(1))        # повторные компании пропускаются
                new.append((self.BASE + href.split("?")[0]) if href.startswith("/") else href.split("?")[0])
        self.log(f"Найдено карточек: {len(new)} (новых)")

        queue = asyncio.Queue()
        for u in new:
            queue.put_nowait(u)
        workers = [asyncio.create_task(self._worker(ctx, queue, city, rubric))
                   for _ in range(max(1, int(self.s["parallel_workers"])))]
        await asyncio.gather(*workers)

    async def _scroll_collect(self, page):
        """Прокручивает список (виртуальный скролл) и копит ссылки по мере появления."""
        collected, stale = {}, 0
        limit = int(self.s.get("max_results") or 0)
        for _ in range(400):
            self._check_stop()
            hrefs = await page.eval_on_selector_all(
                'a[href*="/maps/org/"]', "els => els.map(e => e.getAttribute('href'))")
            before = len(collected)
            for h in hrefs:
                m = ORG_HREF.search(h or "")
                if m:
                    collected.setdefault(m.group(1), h)
            if limit and len(collected) >= limit * 2:
                break
            stale = stale + 1 if len(collected) == before else 0
            if stale >= 6:
                break
            await page.evaluate("""() => {
                const c = document.querySelector('.scroll__container, .search-list-view__list');
                if (c) c.scrollBy(0, 2500); else window.scrollBy(0, 2500);
                const l = document.querySelectorAll('a[href*="/maps/org/"]');
                if (l.length) l[l.length-1].scrollIntoView();
            }""")
            await asyncio.sleep(0.9)
            await self._guard_captcha(page)
        return list(collected.values())

    # ---------- карточки ----------
    async def _worker(self, ctx, queue, city, rubric):
        page = await ctx.new_page()
        try:
            while not queue.empty():
                self._check_stop()
                if self._limit_reached():
                    return
                try:
                    url = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    rec = await self._parse_org(page, url, city, rubric)
                except (StopRequested, CaptchaError):
                    raise
                except Exception as e:
                    self.log(f"Пропуск карточки: {type(e).__name__}")
                    continue
                if rec:
                    if self.s.get("deep_contact_search") and rec.get("site"):
                        await self._deep(rec)
                    self.found += 1
                    self.pair_found += 1
                    self.on_record(rec)
                    self.progress(self.found)
                await self._pause()
        finally:
            await page.close()

    async def _deep(self, rec):
        extra = await asyncio.to_thread(scan_site, rec["site"])
        if extra:
            merge(rec, extra)
            for p in extra.get("phones", []):
                if p not in rec["phones"]:
                    rec["phones"].append(p)

    async def _text(self, page, selectors):
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count():
                    t = (await loc.inner_text(timeout=2500)).strip()
                    if t:
                        return t
            except Exception:
                continue
        return ""

    async def _parse_org(self, page, url, city, rubric):
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await self._guard_captcha(page)
        try:
            await page.wait_for_selector("h1", timeout=12000)
        except Exception:
            return None
        await asyncio.sleep(0.6)
        name = await self._text(page, ["h1.orgpage-header-view__header", "h1"])
        if not name:
            return None
        address = await self._text(page, [".business-contacts-view__address-link",
                                          ".orgpage-header-view__address"])
        category = await self._text(page, [".business-categories-view__category",
                                           ".orgpage-header-view__category"]) or rubric
        rating_raw = await self._text(page, [".business-rating-badge-view__rating-text",
                                             ".business-summary-rating-badge-view__rating-text"])
        reviews_raw = await self._text(page, [".business-rating-amount-view",
                                              ".business-summary-rating-badge-view__rating-count"])
        # кнопка «Показать телефон»
        try:
            btn = page.locator(".card-phones-view__more, .orgpage-phones-view__more").first
            if await btn.count():
                await btn.click(timeout=1500)
        except Exception:
            pass
        phones = []
        try:
            for t in await page.locator(".orgpage-phones-view__phone-number, .card-phones-view__phone-number").all_inner_texts():
                p = normalize_phone(t)
                if p and p not in phones:
                    phones.append(p)
        except Exception:
            pass
        if not phones:
            body = await page.inner_text("body")
            for m in PHONE_RE.findall(body):
                p = normalize_phone(m)
                if p and p not in phones:
                    phones.append(p)
        hrefs = await page.eval_on_selector_all(
            ".business-card-view a[href], .orgpage-view a[href], .business-contacts-view a[href], "
            ".business-urls-view a[href], .business-contacts-view__social-button a[href]",
            "els => els.map(e => e.getAttribute('href'))")
        links = classify_links([h for h in hrefs if h and not h.startswith("/")])
        rating = None
        mr = re.search(r"\d[.,]\d", rating_raw or "")
        if mr:
            rating = float(mr.group(0).replace(",", "."))
        mv = re.search(r"\d+", (reviews_raw or "").replace("\u00a0", ""))
        return {
            "name": name, "category": category, "city": city, "address": address,
            "phones": phones, "site": links["site"], "vk": links["vk"], "tg": links["tg"],
            "wa": links["wa"], "email": links["email"], "rating": rating,
            "reviews": int(mv.group(0)) if mv else None, "url": url,
        }
