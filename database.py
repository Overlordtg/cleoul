import sqlite3
import os
from typing import List, Dict, Any
import config

class GiftsDatabase:
    """
    Универсальный менеджер базы данных.
    Поддерживает облачный Supabase PostgreSQL, а при отсутствии ключей переключается на локальный SQLite.
    """
    def __init__(self, db_path: str = "gifts.db"):
        self.db_path = db_path
        self.use_supabase = False
        self.supabase_client = None

        if config.SUPABASE_URL and config.SUPABASE_KEY and config.SUPABASE_URL != "https://xxxxxxxxx.supabase.co":
            try:
                from supabase import create_client
                self.supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.use_supabase = True
                print("⚡ База данных: Успешное подключение к облаку Supabase PostgreSQL!")
            except Exception as e:
                print(f"⚠️ Не удалось подключиться к Supabase ({e}), переключаемся на локальную SQLite.")
                self.use_supabase = False

        if not self.use_supabase:
            print("💾 База данных: Используется локальная SQLite (gifts.db).")
            self._init_sqlite()

    def _get_sqlite_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_sqlite(self):
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_gifts (
                    gift_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_gift(self, gift_id: str, name: str = "Без названия") -> bool:
        """Добавляет подарок в БД (Supabase или SQLite)."""
        gift_id = gift_id.strip()
        name = name.strip()

        if self.use_supabase:
            try:
                self.supabase_client.table("tracked_gifts").upsert({"gift_id": gift_id, "name": name}).execute()
                return True
            except Exception as e:
                print(f"[Supabase Error] Ошибка добавления подарка {gift_id}: {e}")
                return False
        else:
            try:
                with self._get_sqlite_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO tracked_gifts (gift_id, name)
                        VALUES (?, ?)
                    """, (gift_id, name))
                    conn.commit()
                    return True
            except Exception as e:
                print(f"[SQLite Error] Ошибка добавления подарка {gift_id}: {e}")
                return False

    def remove_gift(self, gift_id: str) -> bool:
        """Удаляет подарок из БД."""
        gift_id = gift_id.strip()

        if self.use_supabase:
            try:
                self.supabase_client.table("tracked_gifts").delete().eq("gift_id", gift_id).execute()
                return True
            except Exception as e:
                print(f"[Supabase Error] Ошибка удаления подарка {gift_id}: {e}")
                return False
        else:
            try:
                with self._get_sqlite_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM tracked_gifts WHERE gift_id = ?", (gift_id,))
                    conn.commit()
                    return True
            except Exception as e:
                print(f"[SQLite Error] Ошибка удаления подарка {gift_id}: {e}")
                return False

    def get_all_gifts(self) -> List[Dict[str, str]]:
        """Возвращает полный список отслеживаемых подарков."""
        if self.use_supabase:
            try:
                response = self.supabase_client.table("tracked_gifts").select("*").order("added_at", desc=True).execute()
                return response.data if response.data else []
            except Exception as e:
                print(f"[Supabase Error] Ошибка получения подарков: {e}")
                return []
        else:
            try:
                with self._get_sqlite_conn() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT gift_id, name, added_at FROM tracked_gifts ORDER BY added_at DESC")
                    rows = cursor.fetchall()
                    return [{"gift_id": row["gift_id"], "name": row["name"], "added_at": row["added_at"]} for row in rows]
            except Exception as e:
                print(f"[SQLite Error] Ошибка получения списка подарков: {e}")
                return []

# Единый объект базы данных
db = GiftsDatabase()
