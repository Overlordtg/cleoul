import asyncio
import re
from typing import Optional, Dict, Any
from pyrogram import Client, filters
from pyrogram.types import Message
import config
from database import db
from state import StateManager
from bot_publisher import TelegramPublisher

class StarsGiftTracker:
    """
    Модуль отслеживания улучшений за Звёзды (Pyrogram MTProto).
    С гибким сопоставлением названий подарков и мгновенным выводом логов.
    """
    def __init__(self):
        self.api_id = config.TELEGRAM_API_ID
        self.api_hash = config.TELEGRAM_API_HASH
        self.session_str = config.TELEGRAM_SESSION_STRING
        self.publisher = TelegramPublisher()
        self.state = StateManager()

    async def start(self):
        if not self.api_id or not self.api_hash or not self.session_str:
            print("⚠️ Pyrogram Stars Tracker: Ожидание подключения TELEGRAM_SESSION_STRING в .env...", flush=True)
            return

        print("⚡ Запуск Pyrogram Stars Tracker (Гибкое сопоставление названий)...", flush=True)

        try:
            app = Client(
                name="stars_tracker_session",
                api_id=self.api_id,
                api_hash=self.api_hash,
                session_string=self.session_str,
                in_memory=True,
                no_updates=True
            )

            @app.on_message()
            async def handle_gift_event(client: Client, message: Message):
                try:
                    parsed = self._parse_event(message)
                    if parsed:
                        allowed_gifts = [g["name"].strip().lower() for g in db.get_all_gifts() if g.get("name")]
                        target_name = parsed["gift_name"].strip().lower()
                        target_clean = re.sub(r"[^\w]", "", target_name)

                        # Гибкая проверка совпадения имени подарка
                        is_match = False
                        if not allowed_gifts:
                            is_match = True  # Если БД пуста, принимаем любые
                        else:
                            for allowed in allowed_gifts:
                                allowed_clean = re.sub(r"[^\w]", "", allowed)
                                if (allowed_clean in target_clean or 
                                    target_clean in allowed_clean or 
                                    any(word in target_name for word in allowed.split() if len(word) > 2)):
                                    is_match = True
                                    break

                        print(f"📡 [Stars Event] Подарок: '{parsed['gift_name']}' #{parsed['number']} | Совпадение с БД: {is_match}", flush=True)

                        if is_match and not self.state.is_seen(parsed["id"]):
                            success = await self.publisher.send_gift_notification(parsed)
                            if success:
                                self.state.mark_seen(parsed["id"])
                except Exception as e:
                    print(f"⚠️ Ошибка обработки события Pyrogram: {e}", flush=True)

            await app.start()
            print("✅ Pyrogram Stars Tracker активно слушает эфир!", flush=True)
        except Exception as e:
            print(f"❌ [Pyrogram Error] Ошибка запуска Stars Tracker: {e}", flush=True)

    def _parse_event(self, message: Message) -> Optional[Dict[str, Any]]:
        text = message.text or message.caption or ""

        if not any(w in text.lower() for w in ["улучшен", "upgraded", "gift", "подарок", "#"]):
            return None

        num_match = re.search(r"#(\d+)", text)
        if not num_match:
            return None
        number = num_match.group(1)

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        gift_name = ""
        model = ""
        symbol = ""
        backdrop = ""

        for line in lines:
            if "#" in line and not gift_name:
                parts = line.split("#")
                gift_name = parts[0].strip()

            if "model" in line.lower() or "модель" in line.lower():
                model = line.split(":", 1)[-1].strip() if ":" in line else line
            elif "symbol" in line.lower() or "символ" in line.lower():
                symbol = line.split(":", 1)[-1].strip() if ":" in line else line
            elif "backdrop" in line.lower() or "background" in line.lower() or "фон" in line.lower():
                backdrop = line.split(":", 1)[-1].strip() if ":" in line else line

        if not gift_name or gift_name.lower() in ["telegram gift", "gift"]:
            first_line = lines[0] if lines else "Gift"
            gift_name = first_line.split("#")[0].strip() if "#" in first_line else first_line

        if not gift_name:
            gift_name = "Gift"
        if not model:
            model = "Собственная модель"
        if not symbol:
            symbol = "Уникальный"
        if not backdrop:
            backdrop = "Уникальный"

        clean_slug = re.sub(r"[^\w]", "", gift_name)
        if not clean_slug:
            clean_slug = "Gift"
        link = f"https://t.me/nft/{clean_slug}-{number}"

        owner = "В профиле Telegram"
        try:
            if hasattr(message, "from_user") and message.from_user and message.from_user.username:
                owner = f"@{message.from_user.username}"
        except Exception:
            pass

        return {
            "id": f"stars_upgrade_{number}_{clean_slug}",
            "gift_name": gift_name,
            "number": number,
            "link": link,
            "full_title": f"{gift_name} #{number}",
            "owner": owner,
            "model": model,
            "symbol": symbol,
            "backdrop": backdrop
        }
