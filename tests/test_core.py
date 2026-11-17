import csv
import tempfile
import unittest
from pathlib import Path

from neo_parser.db import Database
from neo_parser.services import calculate_score, import_csv, normalize_url


class CoreTests(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(normalize_url('example.com'), 'https://example.com')
        self.assertEqual(normalize_url('https://example.com'), 'https://example.com')
        self.assertEqual(normalize_url(''), '')

    def test_csv_import_supports_russian_and_multiline_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'leads.csv'
            path.write_text('Название;Город;Сайт;Заметки\nООО Тест;СПб;example.com;"первая строка\nвторая строка"\n', encoding='utf-8-sig')
            rows = list(import_csv(path))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['company'], 'ООО Тест')
            self.assertEqual(rows[0]['website'], 'https://example.com')
            self.assertIn('вторая строка', rows[0]['notes'])

    def test_database_deduplicates_company_phone_city(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / 'test.sqlite3')
            item = {'company': 'Тест', 'phone': '+70000000000', 'city': 'СПб'}
            self.assertTrue(db.add_lead(item))
            self.assertFalse(db.add_lead(item))
            self.assertEqual(len(db.all()), 1)
            db.conn.close()

    def test_score_is_bounded(self):
        score = calculate_score({'company': 'Тест', 'phone': '1', 'email': 'a@b.ru', 'vk': 'vk', 'category': 'услуги', 'address': 'СПб', 'notes': 'заметка'})
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == '__main__':
    unittest.main()
