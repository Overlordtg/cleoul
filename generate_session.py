import asyncio

# Включаем event loop перед импортом Pyrogram для совместимости с Python 3.12+ / 3.14
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client
import config

async def generate():
    print("=" * 60)
    print("🔑 Генератор строки сессии Telegram Pyrogram")
    print("=" * 60)

    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        print("❌ Ошибка: В файле .env не указаны TELEGRAM_API_ID или TELEGRAM_API_HASH!")
        print("Откройте .env и вставьте значения с сайта my.telegram.org")
        return

    async with Client(
        name="session_generator",
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
        in_memory=True
    ) as app:
        session_str = await app.export_session_string()
        print("\n✅ УСПЕШНО СГЕНЕРИРОВАНО!")
        print("Скопируйте эту строчку и добавьте её в ваш файл .env и в Railway:")
        print("-" * 60)
        print(f"TELEGRAM_SESSION_STRING={session_str}")
        print("-" * 60)

if __name__ == "__main__":
    loop.run_until_complete(generate())
