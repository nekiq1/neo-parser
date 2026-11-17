from pathlib import Path
import sqlite3

APP_DIR = Path.home() / '.neo_parser'
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / 'neo_parser.sqlite3'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS leads (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 company TEXT NOT NULL,
 category TEXT DEFAULT '', city TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT '',
 website TEXT DEFAULT '', vk TEXT DEFAULT '', telegram TEXT DEFAULT '', address TEXT DEFAULT '',
 notes TEXT DEFAULT '', status TEXT DEFAULT 'Новый', score INTEGER DEFAULT 0,
 website_status TEXT DEFAULT '', website_title TEXT DEFAULT '', website_has_form INTEGER DEFAULT 0,
 source TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(company, phone, city)
);
'''

class Database:
    def __init__(self, db_path=DB_PATH):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def add_lead(self, data):
        fields = ['company','category','city','phone','email','website','vk','telegram','address','notes','status','score','source']
        values = [data.get(k, '') for k in fields]
        sql = f"INSERT OR IGNORE INTO leads ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})"
        cur = self.conn.execute(sql, values)
        self.conn.commit()
        return cur.rowcount > 0

    def all(self, query=''):
        if query:
            q = f'%{query}%'
            return self.conn.execute('''SELECT * FROM leads WHERE company LIKE ? OR category LIKE ? OR city LIKE ? OR phone LIKE ? OR website LIKE ? ORDER BY score DESC, company''', (q,q,q,q,q)).fetchall()
        return self.conn.execute('SELECT * FROM leads ORDER BY score DESC, company').fetchall()

    def update_audit(self, lead_id, status, title, has_form, score):
        self.conn.execute('UPDATE leads SET website_status=?, website_title=?, website_has_form=?, score=? WHERE id=?',
                          (status, title, int(has_form), int(score), lead_id))
        self.conn.commit()

    def update_status(self, lead_id, status):
        self.conn.execute('UPDATE leads SET status=? WHERE id=?', (status, lead_id))
        self.conn.commit()

    def delete(self, lead_id):
        self.conn.execute('DELETE FROM leads WHERE id=?', (lead_id,))
        self.conn.commit()
