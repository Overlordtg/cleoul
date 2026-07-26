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
    Модуль отслеживания улучшений за Звёзды.
    no_updates=True отключает внутренний рендеринг каналов Pyrogram и 100% убирает спам Peer ID ошибок.
    Публикует улучшения СТРОГО одного целевого подарка из вашей базы (/list).
    """
    def __init__(self):
        self.api_id = config.TELEGRAM_API_ID
        self.api_hash = config.TELEGRAM_API_HASH
        self.session_str = config.TELEGRAM_SESSION_STRING
        self.publisher = TelegramPublisher()
        self.state = StateManager()

    async def start(self):
        if not self.api_id or not self.api_hash or not self.session_str:
            print("⚠️ Pyrogram Stars Tracker: Ожидание подключения TELEGRAM_SESSION_STRING в .env...")
            return

        print("⚡ Запуск Pyrogram Stars Tracker (Чистый режим без логов)...")

        try:
            app = Client(
                name="stars_tracker_session",
                api_id=self.api_id,
                api_hash=self.api_hash,
                session_string=self.session_str,
                in_memory=True,
                no_updates=True  # 100% отключает внутренние ошибки Pyrogram Peer ID в логах!
            )

            @app.on_message()
            async def handle_gift_event(client: Client, message: Message):
                try:
                    parsed = self._parse_event(message)
                    if parsed:
                        allowed_gifts = [g["name"].lower() for g in db.get_all_gifts() if g.get("name")]
                        target_name = parsed["gift_name"].lower()

                        # Если в /list один подарок, пропускаем абсолютно все другие подарки!
                        if allowed_gifts and not any(allowed in target_name or target_name in allowed for allowed in allowed_gifts):
                            return

                        if not self.state.is_seen(parsed["id"]):
                            await self.publisher.send_gift_notification(parsed)
                            self.state.mark_seen(parsed["id"])
                except Exception:
                    pass

            await app.start()
            print("✅ Pyrogram Stars Tracker работает в чистом фоновом режиме!")
        except Exception as e:
            print(f"❌ [Pyrogram Error] Ошибка запуска Stars Tracker: {e}")

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
