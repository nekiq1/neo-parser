"""Background workers for UI (search + audit)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QThread, Signal

from .db import Database
from .services.audit import audit_website
from .services.scoring import calculate_score
from .services.search import run_search
from .config import AUDIT_TIMEOUT


class SearchWorker(QThread):
    progress = Signal(str, int, int)  # name, found, added
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, query: str, city: str, max_pages: int = 3):
        super().__init__()
        self.query = query
        self.city = city
        self.max_pages = max_pages
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            # Fresh connection in worker thread
            db = Database()
            result = run_search(
                db,
                self.query,
                self.city,
                max_pages=self.max_pages,
                stop_flag=lambda: self._stop,
                on_progress=lambda name, found, added: self.progress.emit(name, found, added),
            )
            db.close()
            self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class AuditWorker(QThread):
    progress = Signal(int, int)  # current, total
    result_ready = Signal(int, dict)  # lead_id, audit dict with score
    finished_all = Signal()

    def __init__(self, rows: list[Any]):
        super().__init__()
        self.rows = rows
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        total = len(self.rows)
        for index, row in enumerate(self.rows, 1):
            if self._stop:
                break
            lead = dict(row)
            audit = audit_website(lead.get("website") or "", timeout=AUDIT_TIMEOUT)
            score, reasons, conf = calculate_score(lead, audit)
            audit["score"] = score
            audit["reasons"] = reasons
            audit["confidence"] = conf
            self.result_ready.emit(lead["id"], audit)
            self.progress.emit(index, total)
        self.finished_all.emit()
