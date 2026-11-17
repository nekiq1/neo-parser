import csv
import io
import re
import socket
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ALIASES = {
    "company": ["company", "name", "название", "компания", "организация"],
    "category": ["category", "категория", "ниша"],
    "city": ["city", "город"],
    "phone": ["phone", "телефон", "номер"],
    "email": ["email", "почта", "e-mail"],
    "website": ["website", "site", "сайт", "url"],
    "vk": ["vk", "вк", "вконтакте"],
    "telegram": ["telegram", "tg", "телеграм"],
    "address": ["address", "адрес"],
    "notes": ["notes", "комментарий", "заметки"],
}


def normalize_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    return value


def import_csv(path):
    """Import UTF-8/UTF-8-BOM, CP1251 and UTF-16 CSV files.

    Delimiter is selected from the header line instead of csv.Sniffer:
    Sniffer can mis-detect short Russian files and multiline quoted cells.
    """
    raw = Path(path).read_bytes()
    text = None
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    else:
        encodings = ("utf-8-sig", "cp1251", "utf-16")

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError("Не удалось определить кодировку CSV")

    first_line = next((line for line in text.splitlines() if line.strip()), "")
    delimiters = (",", ";", "\t")
    delimiter = max(delimiters, key=first_line.count)
    if first_line.count(delimiter) == 0:
        delimiter = ","

    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("В CSV нет заголовков столбцов")

    aliases = {
        target: {name.casefold() for name in names}
        for target, names in ALIASES.items()
    }
    mapping = {}
    for column in reader.fieldnames:
        key = (column or "").strip().lstrip("\ufeff").casefold()
        for target, names in aliases.items():
            if key in names:
                mapping[column] = target
                break

    if "company" not in mapping.values():
        raise ValueError(
            "Не найден столбец компании. Нужен company или Название"
        )

    for row in reader:
        item = {
            target: (row.get(source) or "").strip()
            for source, target in mapping.items()
        }
        item["website"] = normalize_url(item.get("website", ""))
        if item.get("company"):
            yield item


def audit_website(url, timeout=8):
    url = normalize_url(url)
    if not url:
        return ("Нет сайта", "", False)
    try:
        request = Request(
            url, headers={"User-Agent": "NeoParser/0.2 (+website audit)"}
        )
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            body = (
                response.read(350_000).decode("utf-8", "ignore")
                if "text" in content_type or "html" in content_type
                else ""
            )
            title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            title = (
                re.sub(r"\s+", " ", title_match.group(1)).strip()[:160]
                if title_match
                else ""
            )
            has_form = bool(
                re.search(r'<form\b|type=["\'](tel|email)["\']', body, re.I)
            )
            return (f"HTTP {response.status}", title, has_form)
    except HTTPError as error:
        return (f"HTTP {error.code}", "", False)
    except (URLError, socket.timeout, TimeoutError, ValueError, OSError):
        return ("Недоступен", "", False)


def calculate_score(lead, audit_status="", has_form=False):
    score = 0
    if not lead.get("website"):
        score += 35
    elif audit_status and audit_status.startswith("Недоступен"):
        score += 25
    elif audit_status.startswith("HTTP 4") or audit_status.startswith("HTTP 5"):
        score += 20
    if lead.get("phone"):
        score += 12
    if lead.get("email"):
        score += 8
    if lead.get("vk") or lead.get("telegram"):
        score += 8
    if lead.get("category"):
        score += 5
    if lead.get("address"):
        score += 4
    if lead.get("notes"):
        score += 3
    if lead.get("website") and not has_form:
        score += 10
    return min(score, 100)
