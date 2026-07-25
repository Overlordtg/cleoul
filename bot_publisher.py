import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import config

bot = Bot(token=config.BOT_TOKEN) if config.BOT_TOKEN and config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" else None
dp = Dispatcher()

class TelegramPublisher:
    """
    Класс для отправки красивых карточек уведомлений с подробными характеристиками подарков.
    """
    def __init__(self, channel_id: str = config.CHANNEL_ID):
        self.channel_id = channel_id
        self.bot = bot

    async def send_gift_notification(self, gift_info: dict) -> bool:
        if not self.bot:
            print(f"[Bot Console Log] Улучшен новый подарок! {gift_info['full_title']} -> {gift_info['link']}")
            return True

        owner = gift_info.get("owner", "Неизвестен")
        model = gift_info.get("model", "Н/Д")
        symbol = gift_info.get("symbol", "Н/Д")
        backdrop = gift_info.get("backdrop", "Н/Д")
        full_title = gift_info.get("full_title", "Telegram Gift")
        link = gift_info.get("link", "")

        # Красиво скомпонованный текст сообщения по образцу
        text = (
            "<b>Gift Upgrade Alert</b>\n"
            f"🍧 <b>{full_title}</b>\n\n"
            f"👤 <b>Owner:</b> <code>{owner}</code>\n\n"
            f"🎨 <b>Model:</b> {model}\n"
            f"✨ <b>Symbol:</b> {symbol}\n"
            f"🐸 <b>Backdrop:</b> {backdrop}\n\n"
            f"<b>{self.channel_id}</b>"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎁 Посмотреть подарок",
                        url=link
                    )
                ]
            ]
        )

        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
            print(f"[Bot Success] Карточка отправлена в канал: {full_title}")
            return True
        except Exception as e:
            print(f"[Bot Error] Не удалось отправить сообщение в канал {self.channel_id}: {e}")
            return False
