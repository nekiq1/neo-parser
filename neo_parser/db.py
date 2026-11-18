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
    whatsapp TEXT DEFAULT '',
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
        self._migrate_schema()
        self.conn.commit()
        self._seed_categories()
        self.create_daily_backup()

    def create_daily_backup(self, keep: int = 7) -> Path | None:
        """Create one consistent SQLite backup per day and retain the newest copies."""
        from datetime import date

        backup_dir = self.path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f"{self.path.stem}-{date.today().isoformat()}.sqlite3"
        if target.exists():
            return target
        backup_conn = sqlite3.connect(str(target))
        try:
            self.conn.backup(backup_conn)
        finally:
            backup_conn.close()
        backups = sorted(
            backup_dir.glob(f"{self.path.stem}-*.sqlite3"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old in backups[keep:]:
            try:
                old.unlink()
            except OSError:
                pass
        return target

    def _migrate_schema(self) -> None:
        """Add columns introduced in newer app versions without losing user data."""
        columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(leads)").fetchall()
        }
        if "whatsapp" not in columns:
            self.conn.execute("ALTER TABLE leads ADD COLUMN whatsapp TEXT DEFAULT ''")

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
        """Insert a new lead or refresh an existing record without resetting CRM data.

        Returns True only when a new company row was created.
        """
        company = str(data.get("company") or "").strip()
        city = str(data.get("city") or "").strip()
        source_id = str(data.get("source_id") or "").strip()
        phone = str(data.get("phone") or "").strip()
        website = str(data.get("website") or "").strip()

        existing = None
        if source_id:
            existing = self.conn.execute(
                "SELECT id FROM leads WHERE source_id=? AND city=? LIMIT 1",
                (source_id, city),
            ).fetchone()
        if existing is None and phone:
            existing = self.conn.execute(
                "SELECT id FROM leads WHERE phone=? AND city=? LIMIT 1",
                (phone, city),
            ).fetchone()
        if existing is None and website:
            existing = self.conn.execute(
                "SELECT id FROM leads WHERE website=? AND city=? LIMIT 1",
                (website, city),
            ).fetchone()
        if existing is None and company:
            existing = self.conn.execute(
                "SELECT id FROM leads WHERE lower(company)=lower(?) AND city=? LIMIT 1",
                (company, city),
            ).fetchone()

        fields = [
            "company", "category", "city", "phone", "email", "website",
            "vk", "telegram", "whatsapp", "address", "notes", "status", "score",
            "score_reasons", "confidence", "website_status", "website_title",
            "website_has_form", "website_https", "website_mobile",
            "website_portfolio", "website_catalog", "website_contacts",
            "source", "source_id", "card_url", "discovered_at",
        ]
        values = []
        for key in fields:
            value = data.get(key, "")
            if key == "score":
                value = int(value or 0)
            elif key == "confidence":
                value = int(value or 50)
            elif key in ("website_has_form", "website_https", "website_mobile",
                         "website_portfolio", "website_catalog", "website_contacts"):
                value = int(bool(value))
            elif key == "score_reasons" and isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            elif key == "discovered_at" and not value:
                value = _now()
            values.append(value if value is not None else "")

        if existing:
            # Refresh collected facts but retain the user's CRM status and notes.
            update_fields = [
                k for k in fields if k not in ("notes", "status", "discovered_at")
            ]
            update_values = [
                (json.dumps(data.get(k), ensure_ascii=False)
                 if k == "score_reasons" and isinstance(data.get(k), (list, dict))
                 else int(data.get(k) or 0) if k == "score"
                 else int(data.get(k) or 50) if k == "confidence"
                 else int(bool(data.get(k))) if k in (
                     "website_has_form", "website_https", "website_mobile",
                     "website_portfolio", "website_catalog", "website_contacts"
                 )
                 else data.get(k, "") or "")
                for k in update_fields
            ]
            self.conn.execute(
                f"UPDATE leads SET {','.join(k + '=?' for k in update_fields)}, updated_at=? WHERE id=?",
                (*update_values, _now(), existing["id"]),
            )
            self.conn.commit()
            return False

        sql = (
            f"INSERT INTO leads ({','.join(fields)}) "
            f"VALUES ({','.join('?' for _ in fields)})"
        )
        self.conn.execute(sql, values)
        self.conn.commit()
        return True

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
                "OR phone LIKE ? OR email LIKE ? OR website LIKE ? OR address LIKE ? "
                "OR vk LIKE ? OR telegram LIKE ? OR whatsapp LIKE ?)"
            )
            params.extend([q] * 10)
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
