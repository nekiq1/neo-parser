"""Core unit tests — no network, no GUI."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from neo_parser.db import Database
from neo_parser.services.audit import normalize_url
from neo_parser.services.scoring import calculate_score
from neo_parser.sources.base import CompanyResult
from neo_parser.sources.twogis import TwoGisProvider
from neo_parser.sources.twogis_web import _item_to_company, _pass_filters


class NormalizeUrlTests(unittest.TestCase):
    def test_adds_https(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")

    def test_keeps_https(self):
        self.assertEqual(normalize_url("https://example.com/"), "https://example.com")

    def test_empty(self):
        self.assertEqual(normalize_url(""), "")


class ScoringTests(unittest.TestCase):
    def test_no_website_scores_high_but_not_max(self):
        score, reasons, conf = calculate_score({"company": "Test", "phone": "1"})
        self.assertGreaterEqual(score, 30)
        self.assertLessEqual(score, 100)
        self.assertTrue(any("сайт" in r.lower() for r in reasons))

    def test_bounded(self):
        score, _, _ = calculate_score(
            {
                "company": "X",
                "phone": "1",
                "email": "a@b.ru",
                "vk": "vk",
                "category": "y",
                "address": "z",
            },
            {"status": "Недоступен", "reachable": False},
        )
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_good_site_lower_score(self):
        low, _, _ = calculate_score(
            {"company": "X", "website": "https://example.com"},
            {
                "status": "HTTP 200",
                "reachable": True,
                "https": True,
                "mobile": True,
                "portfolio": True,
                "catalog": True,
                "has_form": True,
                "contacts": True,
            },
        )
        high, _, _ = calculate_score(
            {"company": "Y", "website": ""},
            {},
        )
        self.assertLess(low, high)


class DatabaseTests(unittest.TestCase):
    def test_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.sqlite3")
            item = {"company": "Тест", "phone": "+7000", "city": "СПб", "status": "Новый"}
            self.assertTrue(db.add_lead(item))
            self.assertFalse(db.add_lead(item))
            self.assertEqual(len(db.all()), 1)
            db.update_status(1, "Заинтересован")
            refreshed = {**item, "phone": "+7999", "telegram": "https://t.me/test"}
            self.assertFalse(db.add_lead(refreshed))
            row = db.get(1)
            self.assertEqual(row["status"], "Заинтересован")
            self.assertEqual(row["phone"], "+7999")
            self.assertEqual(row["telegram"], "https://t.me/test")
            self.assertEqual(len(db.all()), 1)
            db.close()

    def test_whatsapp_column_and_daily_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.sqlite3")
            self.assertIn("whatsapp", {r["name"] for r in db.conn.execute("PRAGMA table_info(leads)")})
            self.assertTrue((Path(tmp) / "backups").exists())
            db.add_lead({"company": "WA test", "city": "Moscow", "whatsapp": "https://wa.me/123"})
            self.assertEqual(db.all()[0]["whatsapp"], "https://wa.me/123")
            db.close()

    def test_categories_seeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.sqlite3")
            cats = db.categories()
            self.assertIn("Мебель на заказ", cats)
            db.close()

    def test_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.sqlite3")
            db.add_history("Москва", "мебель", 10, 5)
            h = db.history()
            self.assertEqual(len(h), 1)
            self.assertEqual(h[0]["found"], 10)
            db.close()


class ProviderTests(unittest.TestCase):
    def test_not_configured_without_key(self):
        p = TwoGisProvider(api_key="")
        self.assertFalse(p.is_configured())
        self.assertIn("API", p.configuration_help())

    def test_company_result(self):
        c = CompanyResult(name="ООО Тест", city="Москва", source="2GIS")
        self.assertEqual(c.name, "ООО Тест")

    def test_extracts_whatsapp_and_public_contacts(self):
        item = {
            "id": "12345_abc",
            "name": "Тест",
            "contact_groups": [{
                "contacts": [
                    {"type": "whatsapp", "value": "https://wa.me/79990000000"},
                    {"type": "telegram", "value": "https://t.me/test"},
                ]
            }]
        }
        company = _item_to_company(item, "Москва")
        self.assertEqual(company.whatsapp, "https://wa.me/79990000000")
        self.assertEqual(company.telegram, "https://t.me/test")
        self.assertTrue(_pass_filters(company, {"require_public_contact": True}))
        empty = _item_to_company({"name": "Без контактов"}, "Москва")
        self.assertFalse(_pass_filters(empty, {"require_public_contact": True}))


if __name__ == "__main__":
    unittest.main()
