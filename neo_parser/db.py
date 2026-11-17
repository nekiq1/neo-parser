"""SQLite persistence layer."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    category TEXT DEFAULT '',
    city TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    website TEXT DEFAULT '',
    vk TEXT DEFAULT '',
    telegram TEXT DEFAULT '',
    address TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'Новый',
    score INTEGER DEFAULT 0,
    score_reasons TEXT DEFAULT '',
    confidence INTEGER DEFAULT 50,
    website_status TEXT DEFAULT '',
    website_title TEXT DEFAULT '',
    website_has_form INTEGER DEFAULT 0,
    website_https INTEGER DEFAULT 0,
    website_mobile INTEGER DEFAULT 0,
    website_portfolio INTEGER DEFAULT 0,
    website_catalog INTEGER DEFAULT 0,
    website_contacts INTEGER DEFAULT 0,
    source TEXT DEFAULT '',
    source_id TEXT DEFAULT '',
    card_url TEXT DEFAULT '',
    discovered_at TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company, phone, city)
);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT,
    query TEXT,
    found INTEGER DEFAULT 0,
    added INTEGER DEFAULT 0,
    status TEXT DEFAULT 'done',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    is_default INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, db_path: Path | str | None = None):
        path = Path(db_path) if db_path else DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._seed_categories()

    def _seed_categories(self) -> None:
        from .config import DEFAULT_NICHES

        for name in DEFAULT_NICHES:
            self.conn.execute(
                "INSERT OR IGNORE INTO categories (name, is_default) VALUES (?, 1)",
                (name,),
            )
        self.conn.commit()

    # ── leads ──────────────────────────────────────────────
    def add_lead(self, data: dict[str, Any]) -> bool:
        fields = [
            "company", "category", "city", "phone", "email", "website",
            "vk", "telegram", "address", "notes", "status", "score",
            "score_reasons", "confidence", "source", "source_id",
            "card_url", "discovered_at",
        ]
        values = []
        for k in fields:
            v = data.get(k, "")
            if k == "score":
                v = int(v or 0)
            elif k == "confidence":
                v = int(v or 50)
            elif k == "score_reasons" and isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            elif k == "discovered_at" and not v:
                v = _now()
            values.append(v if v is not None else "")

        sql = (
            f"INSERT OR IGNORE INTO leads ({','.join(fields)}) "
            f"VALUES ({','.join('?' for _ in fields)})"
        )
        cur = self.conn.execute(sql, values)
        self.conn.commit()
        return cur.rowcount > 0

    def add_leads_bulk(self, items: Iterable[dict[str, Any]]) -> tuple[int, int]:
        added = 0
        total = 0
        for item in items:
            total += 1
            if self.add_lead(item):
                added += 1
        return total, added

    def all(
        self,
        query: str = "",
        status: str = "",
        city: str = "",
        min_score: int = 0,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            q = f"%{query}%"
            clauses.append(
                "(company LIKE ? OR category LIKE ? OR city LIKE ? "
                "OR phone LIKE ? OR website LIKE ? OR address LIKE ?)"
            )
            params.extend([q] * 6)
        if status and status != "Все статусы":
            clauses.append("status = ?")
            params.append(status)
        if city and city != "Все города":
            clauses.append("city = ?")
            params.append(city)
        if min_score:
            clauses.append("score >= ?")
            params.append(min_score)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM leads{where} ORDER BY score DESC, company"
        return self.conn.execute(sql, params).fetchall()

    def get(self, lead_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()

    def update_audit(self, lead_id: int, audit: dict[str, Any]) -> None:
        self.conn.execute(
            """
            UPDATE leads SET
                website_status=?, website_title=?, website_has_form=?,
                website_https=?, website_mobile=?, website_portfolio=?,
                website_catalog=?, website_contacts=?,
                score=?, score_reasons=?, confidence=?,
                updated_at=?
            WHERE id=?
            """,
            (
                audit.get("status", ""),
                audit.get("title", ""),
                int(audit.get("has_form", False)),
                int(audit.get("https", False)),
                int(audit.get("mobile", False)),
                int(audit.get("portfolio", False)),
                int(audit.get("catalog", False)),
                int(audit.get("contacts", False)),
                int(audit.get("score", 0)),
                json.dumps(audit.get("reasons", []), ensure_ascii=False),
                int(audit.get("confidence", 50)),
                _now(),
                lead_id,
            ),
        )
        self.conn.commit()

    def update_status(self, lead_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE leads SET status=?, updated_at=? WHERE id=?",
            (status, _now(), lead_id),
        )
        self.conn.commit()

    def delete(self, lead_id: int) -> None:
        self.conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
        self.conn.commit()

    def stats(self) -> dict[str, int]:
        total = self.conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        hot = self.conn.execute("SELECT COUNT(*) FROM leads WHERE score >= 60").fetchone()[0]
        with_site = self.conn.execute(
            "SELECT COUNT(*) FROM leads WHERE website != '' AND website IS NOT NULL"
        ).fetchone()[0]
        no_site = total - with_site
        audited = self.conn.execute(
            "SELECT COUNT(*) FROM leads WHERE website_status != ''"
        ).fetchone()[0]
        return {
            "total": total,
            "hot": hot,
            "with_site": with_site,
            "no_site": no_site,
            "audited": audited,
        }

    # ── history ────────────────────────────────────────────
    def add_history(self, city: str, query: str, found: int, added: int, status: str = "done") -> int:
        cur = self.conn.execute(
            "INSERT INTO search_history (city, query, found, added, status) VALUES (?,?,?,?,?)",
            (city, query, found, added, status),
        )
        self.conn.commit()
        return cur.lastrowid

    def history(self, limit: int = 100) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    # ── categories ─────────────────────────────────────────
    def categories(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def add_category(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        try:
            self.conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_category(self, name: str) -> None:
        self.conn.execute("DELETE FROM categories WHERE name=? AND is_default=0", (name,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
