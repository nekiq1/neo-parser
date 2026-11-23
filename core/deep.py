"""Глубокий поиск контактов на сайте компании (главная + страница контактов)."""
import re
import requests
from urllib.parse import urljoin
from .contacts import extract_from_text, PHONE_RE, normalize_phone

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120 Safari/537.36",
           "Accept-Language": "ru-RU,ru;q=0.9"}
_CONTACT_HINT = re.compile(r'href=["\']([^"\']*(?:contact|kontakt|about|o-nas|svyaz)[^"\']*)["\']', re.I)


def _get(url, timeout=8):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code < 400 and "text" in r.headers.get("content-type", "text/html"):
            r.encoding = r.encoding or r.apparent_encoding
            return r.text[:800_000]
    except requests.RequestException:
        pass
    return ""


def scan_site(site: str) -> dict:
    """Возвращает {'vk':[], 'tg':[], 'wa':[], 'email':[], 'phones':[]} со страниц сайта."""
    html = _get(site)
    if not html:
        return {}
    pages = [html]
    for href in list(dict.fromkeys(_CONTACT_HINT.findall(html)))[:2]:
        extra = _get(urljoin(site, href))
        if extra:
            pages.append(extra)
    blob = "\n".join(pages)
    res = extract_from_text(blob)
    phones = []
    for m in PHONE_RE.findall(blob):
        p = normalize_phone(m)
        if p and p not in phones:
            phones.append(p)
    res["phones"] = phones[:3]
    return res
