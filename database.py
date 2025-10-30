# database.py
import sqlite3
import os
from typing import List, Dict, Any, Optional
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QBuffer, QIODevice


class DatabaseManager:
    """Менеджер SQLite для двух таблиц: coffee_beans и brewing_sessions."""

    def __init__(self, db_name: str = "coffee_journal.db"):
        self.db_name = db_name
        # создаём каталог если нужно (например для размещения БД рядом)
        db_dir = os.path.dirname(os.path.abspath(self.db_name))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self.init_database()

    def _connect(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        # включаем FK для текущего соединения
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_database(self) -> None:
        """Инициализация таблиц, если их ещё нет."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coffee_beans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roaster TEXT,
                roast_level TEXT CHECK(roast_level IN ('Light', 'Medium', 'Dark')) DEFAULT 'Medium',
                origin TEXT,
                processing_method TEXT,
                tasting_notes TEXT,
                rating REAL DEFAULT 0,
                price REAL DEFAULT 0,
                purchase_date TEXT,
                image BLOB,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        cur.execute(
            """
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
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (coffee_bean_id) REFERENCES coffee_beans(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()
        conn.close()

    # ---------- Вспомогательные методы ----------
    @staticmethod
    def _pixmap_to_bytes(pix: Optional[QPixmap]) -> Optional[bytes]:
        """Преобразует QPixmap в бинарный PNG или возвращает None."""
        if not pix:
            return None
        if isinstance(pix, QPixmap) and not pix.isNull():
            buf = QBuffer()
            buf.open(QIODevice.WriteOnly)
            # сохраняем в PNG
            pix.save(buf, "PNG")
            data = buf.data()
            buf.close()
            # QByteArray -> bytes
            return bytes(data)
        return None

    # ---------- Методы для coffee_beans ----------
    def add_coffee_bean(
        self,
        name: str,
        roaster: str = "",
        roast_level: str = "Medium",
        origin: str = "",
        processing_method: str = "",
        tasting_notes: str = "",
        rating: float = 0.0,
        price: float = 0.0,
        purchase_date: str = "",
        image: Optional[QPixmap] = None,
    ) -> int:
        """Добавляет запись и возвращает id или -1 при ошибке."""
        conn = self._connect()
        cur = conn.cursor()
        image_data = self._pixmap_to_bytes(image)

        try:
            cur.execute(
                """
                INSERT INTO coffee_beans
                (name, roaster, roast_level, origin, processing_method, tasting_notes,
                 rating, price, purchase_date, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    roaster,
                    roast_level,
                    origin,
                    processing_method,
                    tasting_notes,
                    rating,
                    price,
                    purchase_date,
                    image_data,
                ),
            )
            bean_id = cur.lastrowid
            conn.commit()
            return bean_id
        except sqlite3.Error:
            return -1
        finally:
            conn.close()

    def get_all_coffee_beans(self) -> List[Dict[str, Any]]:
        """Возвращает список словарей с полями таблицы coffee_beans."""
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM coffee_beans ORDER BY created_at DESC")
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def update_coffee_bean(
        self,
        bean_id: int,
        name: Optional[str] = None,
        roaster: Optional[str] = None,
        roast_level: Optional[str] = None,
        origin: Optional[str] = None,
        processing_method: Optional[str] = None,
        tasting_notes: Optional[str] = None,
        rating: Optional[float] = None,
        price: Optional[float] = None,
        purchase_date: Optional[str] = None,
        image: Optional[QPixmap] = None,
    ) -> bool:
        """Обновляет указанные поля записи."""
        conn = self._connect()
        cur = conn.cursor()
        try:
            updates = []
            params = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if roaster is not None:
                updates.append("roaster = ?")
                params.append(roaster)
            if roast_level is not None:
                updates.append("roast_level = ?")
                params.append(roast_level)
            if origin is not None:
                updates.append("origin = ?")
                params.append(origin)
            if processing_method is not None:
                updates.append("processing_method = ?")
                params.append(processing_method)
            if tasting_notes is not None:
                updates.append("tasting_notes = ?")
                params.append(tasting_notes)
            if rating is not None:
                updates.append("rating = ?")
                params.append(rating)
            if price is not None:
                updates.append("price = ?")
                params.append(price)
            if purchase_date is not None:
                updates.append("purchase_date = ?")
                params.append(purchase_date)
            if image is not None:
                img_bytes = self._pixmap_to_bytes(image)
                updates.append("image = ?")
                params.append(img_bytes)

            if not updates:
                return True

            params.append(bean_id)
            query = f"UPDATE coffee_beans SET {', '.join(updates)} WHERE id = ?"
            cur.execute(query, params)
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_coffee_bean(self, bean_id: int) -> bool:
        """Удаляет сорт кофе; связанные сессии удаляются каскадом."""
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM coffee_beans WHERE id = ?", (bean_id,))
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def search_coffee_beans(self, query: str) -> List[Dict[str, Any]]:
        """Поиск по основным текстовым полям."""
        conn = self._connect()
        cur = conn.cursor()
        try:
            p = f"%{query}%"
            cur.execute(
                """
                SELECT * FROM coffee_beans
                WHERE name LIKE ? OR roaster LIKE ? OR origin LIKE ? OR tasting_notes LIKE ?
                ORDER BY created_at DESC
                """,
                (p, p, p, p),
            )
            return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_coffee_with_images_count(self) -> int:
        """Количество записей, где image не NULL."""
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM coffee_beans WHERE image IS NOT NULL")
            res = cur.fetchone()
            return int(res[0]) if res else 0
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    # ---------- Методы для brewing_sessions ----------
    def add_brewing_session(
        self,
        coffee_bean_id: int,
        brew_method: str,
        grind_size: str = "",
        water_temp: int = 0,
        brew_time: int = 0,
        coffee_weight: float = 0.0,
        water_weight: float = 0.0,
        rating: float = 0.0,
        notes: str = "",
    ) -> int:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO brewing_sessions
                (coffee_bean_id, brew_method, grind_size, water_temp, brew_time,
                 coffee_weight, water_weight, rating, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    coffee_bean_id,
                    brew_method,
                    grind_size,
                    water_temp,
                    brew_time,
                    coffee_weight,
                    water_weight,
                    rating,
                    notes,
                ),
            )
            sid = cur.lastrowid
            conn.commit()
            return sid
        except sqlite3.Error:
            return -1
        finally:
            conn.close()

    def get_all_brewing_sessions(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT bs.*, cb.name AS coffee_name
                FROM brewing_sessions bs
                JOIN coffee_beans cb ON bs.coffee_bean_id = cb.id
                ORDER BY bs.created_at DESC
                """
            )
            return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def update_brewing_session(
        self,
        session_id: int,
        coffee_bean_id: Optional[int] = None,
        brew_method: Optional[str] = None,
        grind_size: Optional[str] = None,
        water_temp: Optional[int] = None,
        brew_time: Optional[int] = None,
        coffee_weight: Optional[float] = None,
        water_weight: Optional[float] = None,
        rating: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        try:
            updates = []
            params = []
            if coffee_bean_id is not None:
                updates.append("coffee_bean_id = ?")
                params.append(coffee_bean_id)
            if brew_method is not None:
                updates.append("brew_method = ?")
                params.append(brew_method)
            if grind_size is not None:
                updates.append("grind_size = ?")
                params.append(grind_size)
            if water_temp is not None:
                updates.append("water_temp = ?")
                params.append(water_temp)
            if brew_time is not None:
                updates.append("brew_time = ?")
                params.append(brew_time)
            if coffee_weight is not None:
                updates.append("coffee_weight = ?")
                params.append(coffee_weight)
            if water_weight is not None:
                updates.append("water_weight = ?")
                params.append(water_weight)
            if rating is not None:
                updates.append("rating = ?")
                params.append(rating)
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)

            if not updates:
                return True

            params.append(session_id)
            query = f"UPDATE brewing_sessions SET {', '.join(updates)} WHERE id = ?"
            cur.execute(query, params)
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_brewing_session(self, session_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM brewing_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def search_brewing_sessions(self, query: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            p = f"%{query}%"
            cur.execute(
                """
                SELECT bs.*, cb.name AS coffee_name
                FROM brewing_sessions bs
                JOIN coffee_beans cb ON bs.coffee_bean_id = cb.id
                WHERE cb.name LIKE ? OR bs.brew_method LIKE ? OR bs.notes LIKE ?
                ORDER BY bs.created_at DESC
                """,
                (p, p, p),
            )
            return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_detailed_statistics(self) -> Dict[str, Any]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM coffee_beans")
            total_beans = cur.fetchone()[0] or 0

            cur.execute("SELECT AVG(rating) FROM coffee_beans WHERE rating > 0")
            avg_bean = cur.fetchone()[0]
            avg_bean_rating = round(avg_bean, 1) if avg_bean else 0

            cur.execute("SELECT AVG(price) FROM coffee_beans WHERE price > 0")
            avg_price_val = cur.fetchone()[0]
            avg_price = round(avg_price_val, 0) if avg_price_val else 0

            cur.execute("SELECT COUNT(*) FROM brewing_sessions")
            total_sessions = cur.fetchone()[0] or 0

            cur.execute("SELECT AVG(rating) FROM brewing_sessions WHERE rating > 0")
            avg_sess = cur.fetchone()[0]
            avg_session_rating = round(avg_sess, 1) if avg_sess else 0

            return {
                "total_beans": total_beans,
                "total_sessions": total_sessions,
                "avg_bean_rating": avg_bean_rating,
                "avg_session_rating": avg_session_rating,
                "avg_price": avg_price,
            }
        except sqlite3.Error:
            return {
                "total_beans": 0,
                "total_sessions": 0,
                "avg_bean_rating": 0,
                "avg_session_rating": 0,
                "avg_price": 0,
            }
        finally:
            conn.close()
