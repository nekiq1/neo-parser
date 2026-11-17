"""CSV / XLSX export."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


FIELDS = [
    "company", "category", "city", "phone", "email", "website",
    "vk", "telegram", "address", "status", "score", "score_reasons",
    "confidence", "website_status", "website_title", "source",
    "card_url", "discovered_at", "notes",
]

HEADERS_RU = {
    "company": "Компания",
    "category": "Категория",
    "city": "Город",
    "phone": "Телефон",
    "email": "Email",
    "website": "Сайт",
    "vk": "VK",
    "telegram": "Telegram",
    "address": "Адрес",
    "status": "Статус",
    "score": "Оценка",
    "score_reasons": "Причины оценки",
    "confidence": "Уверенность",
    "website_status": "Статус сайта",
    "website_title": "Title сайта",
    "source": "Источник",
    "card_url": "Карточка",
    "discovered_at": "Дата обнаружения",
    "notes": "Заметки",
}


def _row_dict(row) -> dict:
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    return dict(row)


def export_csv(rows: Iterable, path: str | Path) -> int:
    path = Path(path)
    if path.suffix.lower() != ".csv":
        path = path.with_suffix(".csv")
    count = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";", extrasaction="ignore")
        writer.writerow({k: HEADERS_RU.get(k, k) for k in FIELDS})
        for row in rows:
            d = _row_dict(row)
            writer.writerow({k: d.get(k, "") for k in FIELDS})
            count += 1
    return count


def export_xlsx(rows: Iterable, path: str | Path) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    path = Path(path)
    if path.suffix.lower() not in (".xlsx", ".xlsm"):
        path = path.with_suffix(".xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    headers = [HEADERS_RU.get(k, k) for k in FIELDS]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    count = 0
    for row in rows:
        d = _row_dict(row)
        ws.append([d.get(k, "") for k in FIELDS])
        count += 1

    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 2, 12), 48)

    wb.save(path)
    return count
