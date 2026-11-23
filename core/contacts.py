"""Извлечение и классификация контактов: сайт / VK / Telegram / WhatsApp / email / телефон."""
import re
from urllib.parse import urlparse, unquote

VK_RE = re.compile(r'https?://(?:www\.|m\.)?(?:vk\.com|vk\.ru|vkontakte\.ru)/[^\s"\'<>)\]]+', re.I)
TG_RE = re.compile(r'https?://(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/[^\s"\'<>)\]]+', re.I)
TG_SCHEME_RE = re.compile(r'tg://resolve\?domain=([A-Za-z0-9_]{4,32})', re.I)
WA_RE = re.compile(r'https?://(?:wa\.me|api\.whatsapp\.com|web\.whatsapp\.com|chat\.whatsapp\.com|whatsapp\.com)/[^\s"\'<>)\]]+', re.I)
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
PHONE_RE = re.compile(r'(?:\+7|8)[\s\-()]*\d{3}[\s\-()]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}')

# Домены, которые не считаются «собственным сайтом» компании
SOCIAL_HOSTS = ("vk.com", "vk.ru", "vkontakte.ru", "t.me", "telegram.me", "telegram.dog",
                "wa.me", "whatsapp.com", "instagram.com", "facebook.com", "ok.ru",
                "youtube.com", "youtu.be", "twitter.com", "x.com", "tiktok.com",
                "dzen.ru", "zen.yandex.ru", "yandex.ru", "ya.ru", "2gis.ru", "2gis.com",
                "google.com", "goo.gl", "taplink.cc", "linktr.ee", "avito.ru")
_TG_SKIP = {"share", "joinchat", "addstickers", "s", "iv", "proxy", "socks", "login"}
_VK_SKIP = {"share.php", "away.php", "widget", "id0", "club0", "feed", "login", "about"}
_FILE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")


def _clean_url(u: str) -> str:
    return u.strip().rstrip(".,;:!?)\"'").replace("&amp;", "&")


def _uniq(items):
    seen, out = set(), []
    for i in items:
        if i and i.lower() not in seen:
            seen.add(i.lower())
            out.append(i)
    return out


def normalize_phone(raw: str) -> str:
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 11 and d[0] in "78":
        d = "7" + d[1:]
    elif len(d) == 10:
        d = "7" + d
    return "+" + d if len(d) == 11 else ""


def normalize_site(url: str) -> str:
    """Возвращает URL собственного сайта или '' если это соцсеть/агрегатор."""
    if not url:
        return ""
    url = _clean_url(url)
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if not host or "." not in host:
        return ""
    host = host[4:] if host.startswith("www.") else host
    if any(host == h or host.endswith("." + h) for h in SOCIAL_HOSTS):
        return ""
    return url


def clean_vk(url: str) -> str:
    p = urlparse(_clean_url(url))
    path = p.path.strip("/")
    if not path or path.split("/")[0].lower() in _VK_SKIP:
        return ""
    return f"https://vk.com/{path}"


def clean_tg(url: str) -> str:
    path = unquote(urlparse(_clean_url(url)).path).strip("/")
    first = path.split("/")[0] if path else ""
    if not first or first.lower() in _TG_SKIP or first.startswith("+"):
        return ""
    return f"https://t.me/{first}"


def clean_wa(url: str) -> str:
    url = _clean_url(url)
    m = re.search(r"wa\.me/\+?(\d{10,15})", url)
    if m:
        return f"https://wa.me/{m.group(1)}"
    m = re.search(r"[?&]phone=\+?(\d{10,15})", url)
    if m:
        return f"https://wa.me/{m.group(1)}"
    if "chat.whatsapp.com" in url.lower():
        return url
    return ""


def extract_from_text(text: str) -> dict:
    """Достаёт мессенджеры и почту из произвольного HTML/текста."""
    text = text or ""
    vk = [clean_vk(u) for u in VK_RE.findall(text)]
    tg = [clean_tg(u) for u in TG_RE.findall(text)]
    tg += [f"https://t.me/{h}" for h in TG_SCHEME_RE.findall(text)]
    wa = [clean_wa(u) for u in WA_RE.findall(text)]
    emails = [e.lower() for e in EMAIL_RE.findall(text) if not e.lower().endswith(_FILE_EXT)]
    return {"vk": _uniq(vk), "tg": _uniq(tg), "wa": _uniq(wa), "email": _uniq(emails)}


def classify_links(links) -> dict:
    """links — список href со страницы организации. Возвращает сайт и соцсети."""
    links = [l for l in links if l]
    res = {"site": ""}
    res.update(extract_from_text("\n".join(links)))
    for l in links:
        if re.match(r"^https?://", l, re.I):
            s = normalize_site(l)
            if s:
                res["site"] = s
                break
    return res


def merge(base: dict, extra: dict) -> dict:
    for k in ("vk", "tg", "wa", "email"):
        base[k] = _uniq(list(base.get(k) or []) + list(extra.get(k) or []))
    return base
