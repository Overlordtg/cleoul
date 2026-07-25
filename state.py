import json
import os
from typing import Set

STATE_FILE = "seen_gifts.json"

class StateManager:
    """
    Класс для хранения и дедупликации уже обработанных минтов/улучшений подарков.
    Сохраняет список уникальных ID в локальный JSON-файл.
    """
    def __init__(self, filename: str = STATE_FILE):
        self.filename = filename
        self.seen_ids: Set[str] = self._load()

    def _load(self) -> Set[str]:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data)
            except Exception as e:
                print(f"[State Warning] Не удалось загрузить state ({e}), создаем новый.")
                return set()
        return set()

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_ids), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[State Error] Ошибка сохранения state: {e}")

    def is_seen(self, item_id: str) -> bool:
        return item_id in self.seen_ids

    def mark_seen(self, item_id: str):
        self.seen_ids.add(item_id)
        if len(self.seen_ids) > 5000:
            self.seen_ids = set(list(self.seen_ids)[-2500:])
        self.save()
