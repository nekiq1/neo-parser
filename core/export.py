"""Экспорт результатов в XLSX и чтение ранее сохранённых баз."""
import re
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

COLUMNS = [
    ("name", "Название"), ("category", "Рубрика"), ("city", "Город"), ("address", "Адрес"),
    ("phones", "Телефоны"), ("site", "Сайт"), ("vk", "VK"), ("tg", "Telegram"),
    ("wa", "WhatsApp"), ("email", "Email"), ("rating", "Рейтинг"), ("reviews", "Отзывы"),
    ("url", "Яндекс Карты"),
]


def _cell(v):
    if isinstance(v, (list, tuple)):
        return "\n".join(str(x) for x in v)
    return v if v is not None else ""


def safe_name(s: str) -> str:
    return re.sub(r"[^\w\-]+", "_", s, flags=re.U).strip("_")[:60] or "base"


def save_xlsx(records, directory: Path, title: str = "neo") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Neo parser"
    ws.append([h for _, h in COLUMNS])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2B2B2B")
    for r in records:
        ws.append([_cell(r.get(k)) for k, _ in COLUMNS])
    widths = [34, 24, 16, 40, 24, 28, 30, 28, 28, 28, 9, 9, 40]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    path = directory / f"{safe_name(title)}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    wb.save(path)
    return path


def list_bases(directory: Path):
    out = []
    for p in sorted(directory.glob("*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True):
        out.append({"name": p.name, "size": p.stat().st_size,
                    "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M")})
    return out


def load_base(path: Path):
    # Передаём собственный file object: на Windows это гарантирует закрытие
    # файлового дескриптора даже для read_only workbook и позволяет сразу
    # переименовать/удалить XLSX после чтения.
    with Path(path).open("rb") as source:
        wb = load_workbook(source, read_only=True, data_only=True)
        try:
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            rev = {h: k for k, h in COLUMNS}
            keys = [rev.get(str(h)) for h in rows[0]]
            recs = []
            for row in rows[1:]:
                rec = {}
                for k, v in zip(keys, row):
                    if not k or v in (None, ""):
                        continue
                    if k in ("phones", "vk", "tg", "wa", "email"):
                        rec[k] = [x for x in str(v).splitlines() if x]
                    else:
                        rec[k] = v
                if rec:
                    recs.append(rec)
            return recs
        finally:
            wb.close()
