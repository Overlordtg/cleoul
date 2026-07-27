import sqlite3
import httpx
from supabase import create_client, Client, ClientOptions
from typing import List, Dict, Any
import config

class GiftsDatabase:
    """
    Универсальный менеджер базы данных.
    Работает с облачной PostgreSQL через Supabase.
    Поддерживает fallback на локальный SQLite при сбоях.
    """
    def __init__(self, db_path: str = "gifts.db"):
        self.db_path = db_path
        self.supabase: Client = None

        if config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                # Включаем httpx.Client(verify=False) для предотвращения SSL ошибок на серверах и ПК
                options = ClientOptions(httpx_client=httpx.Client(verify=False))
                self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY, options=options)
                print("⚡ База данных: Успешное подключение к облаку Supabase PostgreSQL!", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка подключения к Supabase ({e}), переключение на локальный SQLite.", flush=True)

        self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gifts (
                    gift_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_gift(self, gift_id: str, name: str) -> bool:
        gift_id = gift_id.strip()
        name = name.strip()
        
        # 1. Запись в SQLite
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO gifts (gift_id, name)
                    VALUES (?, ?)
                """, (gift_id, name))
                conn.commit()
        except Exception as e:
            print(f"❌ [SQLite Error] {e}", flush=True)

        # 2. Синхронизация с Supabase
        if self.supabase:
            try:
                self.supabase.table("tracked_gifts").upsert({
                    "gift_id": gift_id,
                    "name": name
                }).execute()
                print(f"✅ [Supabase] Подарок '{name}' ({gift_id}) успешно сохранен в облачную БД!", flush=True)
                return True
            except Exception as e:
                print(f"⚠️ [Supabase Upsert Error] {e}", flush=True)
                return True

        return True

    def remove_gift(self, gift_id: str) -> bool:
        gift_id = gift_id.strip()

        # 1. Удаление из SQLite
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM gifts WHERE gift_id = ?", (gift_id,))
                conn.commit()
        except Exception as e:
            print(f"❌ [SQLite Delete Error] {e}", flush=True)

        # 2. Удаление из Supabase
        if self.supabase:
            try:
                self.supabase.table("tracked_gifts").delete().eq("gift_id", gift_id).execute()
                print(f"✅ [Supabase] Подарок {gift_id} удален из БД!", flush=True)
                return True
            except Exception as e:
                print(f"⚠️ [Supabase Delete Error] {e}", flush=True)

        return True

    def get_all_gifts(self) -> List[Dict[str, Any]]:
        # Сначала пробуем запросить из Supabase
        if self.supabase:
            try:
                response = self.supabase.table("tracked_gifts").select("*").execute()
                if response.data is not None and len(response.data) > 0:
                    return response.data
            except Exception as e:
                print(f"⚠️ [Supabase Fetch Error] {e}", flush=True)

        # Фолбек на SQLite
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT gift_id, name, added_at FROM gifts")
                rows = cursor.fetchall()
                return [{"gift_id": row["gift_id"], "name": row["name"], "added_at": row["added_at"]} for row in rows]
        except Exception as e:
            print(f"❌ [SQLite Fetch Error] {e}", flush=True)
            return []

db = GiftsDatabase()
