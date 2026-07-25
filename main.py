import asyncio
from datetime import datetime
from aiogram.exceptions import TelegramUnauthorizedError, TelegramAPIError
import config
from state import StateManager
from ton_client import TonGiftFetcher
from bot_publisher import TelegramPublisher, bot, dp
from admin_handlers import router as admin_router

# Регистрируем роутер команд админки в главном файле
dp.include_router(admin_router)

async def monitor_loop():
    """Фоновый цикл мониторинга новых минтов подарков."""
    state = StateManager()
    fetcher = TonGiftFetcher()
    publisher = TelegramPublisher()

    print("📡 Фоновый монитор минтов подарков запущен и активен.")

    while True:
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            latest_gifts = await fetcher.fetch_latest_gift_mints(limit=20)
            
            new_count = 0
            for gift in reversed(latest_gifts):
                gift_id = gift["id"]

                if not state.is_seen(gift_id):
                    success = await publisher.send_gift_notification(gift)
                    if success:
                        state.mark_seen(gift_id)
                        new_count += 1

            if new_count > 0:
                print(f"[{timestamp}] 🎉 Обнаружено и опубликовано новых улучшений: {new_count}")
            else:
                print(f"[{timestamp}] 🔍 Опрос API завершен: новых улучшений не обнаружено.")

        except Exception as e:
            print(f"⚠️ Ошибка в мониторе: {e}")

        await asyncio.sleep(config.POLL_INTERVAL)

async def main():
    print("=" * 60)
    print("🚀 Запуск бота с административной панелью и фоновым монитором")
    print(f"📁 Папка проекта: C:\\gifts\\upgrade1")
    print(f"⏱ Интервал опроса: {config.POLL_INTERVAL} сек.")
    print(f"📢 Канал назначения: {config.CHANNEL_ID}")
    print("=" * 60)

    if not bot:
        print("❌ Ошибка: В файле .env не указан BOT_TOKEN!")
        return

    # Проверка авторизации бота
    try:
        me = await bot.get_me()
        print(f"✅ Успешная авторизация бота: @{me.username} ({me.first_name})")
    except TelegramUnauthorizedError:
        print("\n❌ ОШИБКА АВТОРИЗАЦИИ ТЕЛЕГРАМ: Указан неверный BOT_TOKEN в .env!\n")
        return
    except TelegramAPIError as e:
        print(f"\n⚠️ Ошибка подключения к Telegram API: {e}\n")
        return
    except Exception as e:
        print(f"\n⚠️ Ошибка при подключении: {e}\n")
        return

    if config.CHANNEL_ID == "@my_gift_feed_channel" or "@your_channel_username" in config.CHANNEL_ID:
        print("⚠️ ВНИМАНИЕ: Замените CHANNEL_ID в .env на юзернейм вашего реального Telegram-канала!\n")

    monitor_task = asyncio.create_task(monitor_loop())

    try:
        print("🤖 Бот готов! Отправьте ему /test для проверки поста или /start для управления.")
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        await bot.session.close()
        print("✅ Бот и монитор остановлены.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
