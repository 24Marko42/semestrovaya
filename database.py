# database.py
import sqlite3
import os, sys, shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QBuffer, QIODevice

# helper for resources (works with PyInstaller)
def resource_path(rel):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, rel)

def get_user_db_path(filename="coffee_journal.db"):
    # use local appdata for persistence on Windows; fallback to cwd
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.path.expanduser("~")
    appdir = os.path.join(base, "CoffeeJournal")
    os.makedirs(appdir, exist_ok=True)
    return os.path.join(appdir, filename)

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.template_db = resource_path(os.path.join("ui", "db_template.sqlite"))  # optional template
        self.db_path = db_path or get_user_db_path()
        # if db not exists and template shipped — copy it
        if not os.path.exists(self.db_path) and os.path.exists(self.template_db):
            try:
                shutil.copyfile(self.template_db, self.db_path)
            except Exception:
                pass
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS coffee_beans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roaster TEXT,
                roast_level TEXT,
                origin TEXT,
                processing_method TEXT,
                tasting_notes TEXT,
                rating REAL DEFAULT 0,
                price REAL,
                purchase_date TEXT,
                image BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS brewing_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coffee_bean_id INTEGER NOT NULL,
                brew_method TEXT NOT NULL,
                grind_size TEXT,
                water_temp INTEGER,
                brew_time INTEGER,
                coffee_weight REAL,
                water_weight REAL,
                rating REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (coffee_bean_id) REFERENCES coffee_beans(id) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()

    def _pixmap_to_bytes(self, pix: QPixmap) -> Optional[bytes]:
        if pix is None or pix.isNull():
            return None
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        pix.save(buf, "PNG")
        data = bytes(buf.data())
        buf.close()
        return data

    def add_coffee_bean(self, name, roaster="", roast_level="Medium", origin="", processing_method="",
                        tasting_notes="", rating=0.0, price=0.0, purchase_date="", image: QPixmap = None) -> int:
        img = None
        if isinstance(image, QPixmap):
            img = self._pixmap_to_bytes(image)
        try:
            c = self.conn.cursor()
            c.execute('''
                INSERT INTO coffee_beans (name, roaster, roast_level, origin, processing_method,
                                          tasting_notes, rating, price, purchase_date, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, roaster, roast_level, origin, processing_method, tasting_notes, rating, price, purchase_date, img))
            self.conn.commit()
            return c.lastrowid
        except Exception:
            return -1

    def get_all_coffee_beans(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute('SELECT * FROM coffee_beans ORDER BY created_at DESC')
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def update_coffee_bean(self, bean_id, **kwargs) -> bool:
        if not kwargs:
            return True
        fields = []
        vals = []
        for k, v in kwargs.items():
            if k == "image" and isinstance(v, QPixmap):
                v = self._pixmap_to_bytes(v)
            fields.append(f"{k} = ?")
            vals.append(v)
        vals.append(bean_id)
        try:
            self.conn.cursor().execute(f"UPDATE coffee_beans SET {', '.join(fields)} WHERE id = ?", vals)
            self.conn.commit()
            return True
        except Exception:
            return False

    def delete_coffee_bean(self, bean_id) -> bool:
        try:
            c = self.conn.cursor()
            c.execute('DELETE FROM coffee_beans WHERE id = ?', (bean_id,))
            self.conn.commit()
            return c.rowcount > 0
        except Exception:
            return False

    def search_coffee_beans(self, q: str):
        pat = f"%{q}%"
        c = self.conn.cursor()
        c.execute('SELECT * FROM coffee_beans WHERE name LIKE ? OR roaster LIKE ? OR origin LIKE ? OR tasting_notes LIKE ? ORDER BY created_at DESC',
                  (pat, pat, pat, pat))
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in c.fetchall()]

    def get_coffee_with_images_count(self):
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM coffee_beans WHERE image IS NOT NULL')
        r = c.fetchone()
        return r[0] if r else 0

    # brewing sessions
    def add_brewing_session(self, coffee_bean_id, brew_method, grind_size="", water_temp=0, brew_time=0,
                            coffee_weight=0.0, water_weight=0.0, rating=0.0, notes="") -> int:
        try:
            c = self.conn.cursor()
            c.execute('''
                INSERT INTO brewing_sessions
                (coffee_bean_id, brew_method, grind_size, water_temp, brew_time, coffee_weight, water_weight, rating, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (coffee_bean_id, brew_method, grind_size, water_temp, brew_time, coffee_weight, water_weight, rating, notes))
            self.conn.commit()
            return c.lastrowid
        except Exception:
            return -1

    def get_all_brewing_sessions(self):
        c = self.conn.cursor()
        c.execute('SELECT bs.*, cb.name as coffee_name FROM brewing_sessions bs JOIN coffee_beans cb ON bs.coffee_bean_id = cb.id ORDER BY bs.created_at DESC')
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in c.fetchall()]

    def update_brewing_session(self, session_id, **kwargs) -> bool:
        if not kwargs:
            return True
        fields = []; vals = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?"); vals.append(v)
        vals.append(session_id)
        try:
            self.conn.cursor().execute(f"UPDATE brewing_sessions SET {', '.join(fields)} WHERE id = ?", vals)
            self.conn.commit()
            return True
        except Exception:
            return False

    def delete_brewing_session(self, session_id) -> bool:
        try:
            c = self.conn.cursor(); c.execute('DELETE FROM brewing_sessions WHERE id = ?', (session_id,)); self.conn.commit(); return c.rowcount>0
        except Exception:
            return False

    def search_brewing_sessions(self, q: str):
        pat = f"%{q}%"
        c = self.conn.cursor()
        c.execute('SELECT bs.*, cb.name as coffee_name FROM brewing_sessions bs JOIN coffee_beans cb ON bs.coffee_bean_id = cb.id WHERE cb.name LIKE ? OR bs.brew_method LIKE ? OR bs.notes LIKE ? ORDER BY bs.created_at DESC',
                  (pat, pat, pat))
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in c.fetchall()]

    def get_detailed_statistics(self):
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM coffee_beans'); total_beans = c.fetchone()[0]
        c.execute('SELECT AVG(rating) FROM coffee_beans WHERE rating>0'); avg_bean = c.fetchone()[0] or 0
        c.execute('SELECT AVG(price) FROM coffee_beans WHERE price>0'); avg_price = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM brewing_sessions'); total_sessions = c.fetchone()[0]
        c.execute('SELECT AVG(rating) FROM brewing_sessions WHERE rating>0'); avg_sess = c.fetchone()[0] or 0
        return {"total_beans": total_beans, "avg_bean_rating": round(avg_bean,1), "avg_price": round(avg_price,0), "total_sessions": total_sessions, "avg_session_rating": round(avg_sess,1)}
