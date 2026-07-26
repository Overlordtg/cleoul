import asyncio
import re
from typing import Optional, Dict, Any
from pyrogram import Client, filters
from pyrogram.types import Message
import config
from state import StateManager
from bot_publisher import TelegramPublisher

class StarsGiftTracker:
    """
    Модуль отслеживания моментальных улучшений подарков за Звёзды (Stars)
    внутри Telegram в реальном времени через Pyrogram MTProto API.
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

        print("⚡ Запуск Pyrogram Stars Tracker (Мониторинг апгрейдов за Звёзды)...")

        try:
            app = Client(
                name="stars_tracker_session",
                api_id=self.api_id,
                api_hash=self.api_hash,
                session_string=self.session_str,
                in_memory=True
            )

            @app.on_message()
            async def handle_gift_event(client: Client, message: Message):
                text = message.text or message.caption or ""
                if any(word in text.lower() for word in ["улучшен", "upgraded", "gift", "подарок"]):
                    parsed = self._parse_event(message, text)
                    if parsed and not self.state.is_seen(parsed["id"]):
                        await self.publisher.send_gift_notification(parsed)
                        self.state.mark_seen(parsed["id"])

            await app.start()
            print("✅ Pyrogram Stars Tracker успешно подключен к серверам Telegram и слушает эфир!")
        except Exception as e:
            print(f"❌ [Pyrogram Error] Ошибка запуска Stars Tracker: {e}")

    def _parse_event(self, message: Message, text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"^(.*?)\s*#(\d+)$", text.strip(), re.MULTILINE)
        if match:
            gift_name = match.group(1).strip()
            number = match.group(2).strip()
        else:
            gift_name = "Telegram Gift"
            number = str(message.id)

        clean_name = gift_name.replace("'", "").replace("’", "").replace("`", "")
        words = clean_name.split()
        formatted_name = "".join(word.capitalize() for word in words)
        link = f"https://t.me/nft/{formatted_name}-{number}"

        return {
            "id": f"stars_upgrade_{message.id}_{number}",
            "gift_name": gift_name,
            "number": number,
            "link": link,
            "full_title": f"{gift_name} #{number}",
            "owner": getattr(message.from_user, "username", "В профиле Telegram") if hasattr(message, "from_user") and message.from_user else "В профиле Telegram",
            "model": "Эксклюзивная (за Звёзды)",
            "symbol": "Стандартный",
            "backdrop": "Стандартный"
        }
