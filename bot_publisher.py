import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import config

bot = Bot(token=config.BOT_TOKEN) if config.BOT_TOKEN and config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" else None
dp = Dispatcher()

class TelegramPublisher:
    """
    Класс для отправки карточек уведомлений с интегрированной гиперссылкой в заголовке,
    формирующей встроенное превью картинки Telegram.
    """
    def __init__(self, channel_id: str = config.CHANNEL_ID):
        self.channel_id = channel_id
        self.bot = bot

    async def send_gift_notification(self, gift_info: dict) -> bool:
        if not self.bot:
            print(f"[Bot Console Log] Улучшен новый подарок! {gift_info['full_title']} -> {gift_info['link']}")
            return True

        owner = gift_info.get("owner", "В профиле Telegram")
        model = gift_info.get("model", "—")
        symbol = gift_info.get("symbol", "—")
        backdrop = gift_info.get("backdrop", "—")
        full_title = gift_info.get("full_title", "Telegram Gift")
        link = gift_info.get("link", "https://t.me")

        # Telegram HTML парсер требует строго двойные кавычки в <a href="..."> для создания гиперссылки и превью!
        text = (
            "<b>Gift Upgrade Alert</b>\n"
            f'🎁 <a href="{link}"><b>{full_title}</b></a>\n\n'
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
            print(f"[Bot Success] Карточка с кликабельным заголовком и превью отправлена в канал: {full_title}")
            return True
        except Exception as e:
            print(f"[Bot Error] Не удалось отправить сообщение в канал {self.channel_id}: {e}")
            return False
