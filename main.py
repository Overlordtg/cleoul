import asyncio
import os
import sys
from datetime import datetime
from aiogram.exceptions import TelegramUnauthorizedError, TelegramAPIError
import config
from state import StateManager
from ton_client import TonGiftFetcher
from stars_tracker import StarsGiftTracker
from bot_publisher import TelegramPublisher, bot, dp
from admin_handlers import router as admin_router

# Включаем небуферизованный вывод логов в реальном времени для Railway
sys.stdout.reconfigure(line_buffering=True)

dp.include_router(admin_router)

async def monitor_loop():
    """Фоновый цикл мониторинга минтов подарков."""
    state = StateManager()
    fetcher = TonGiftFetcher()
    publisher = TelegramPublisher()

    print("📡 Фоновый монитор минтов подарков запущен.", flush=True)

    print("🌱 Инициализация: загружаем текущие исторические подарки...", flush=True)
    try:
        initial_gifts = await fetcher.fetch_latest_gift_mints(limit=50)
        for gift in initial_gifts:
            state.mark_seen(gift["id"])
        print(f"✅ Инициализация завершена. Пропущено старых минтов: {len(initial_gifts)}. Ожидание новых апгрейдов...", flush=True)
    except Exception as e:
        print(f"⚠️ Предупреждение при инициализации: {e}", flush=True)

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
                print(f"[{timestamp}] 🎉 Обнаружено и опубликовано новых живых улучшений: {new_count}", flush=True)
            else:
                print(f"[{timestamp}] 🔍 Опрос API: новых улучшений не обнаружено.", flush=True)

        except Exception as e:
            print(f"⚠️ Ошибка в мониторе: {e}", flush=True)

        await asyncio.sleep(config.POLL_INTERVAL)

async def main():
    token_status = f"{config.BOT_TOKEN[:6]}..." if config.BOT_TOKEN and config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" else "НЕ ЗАДАН (Пусто)"

    print("=" * 60, flush=True)
    print("🚀 Запуск бота с административной панелью, фоновым монитором и Stars Tracker", flush=True)
    print(f"🔑 Статус BOT_TOKEN: {token_status}", flush=True)
    print(f"⏱ Интервал опроса: {config.POLL_INTERVAL} сек.", flush=True)
    print(f"📢 Канал назначения: {config.CHANNEL_ID}", flush=True)
    print("=" * 60, flush=True)

    if not bot or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Ошибка: Переменная BOT_TOKEN не установлена!", flush=True)
        return

    try:
        me = await bot.get_me()
        print(f"✅ Успешная авторизация бота: @{me.username} ({me.first_name})", flush=True)
    except TelegramUnauthorizedError:
        print("\n❌ ОШИБКА АВТОРИЗАЦИИ ТЕЛЕГРАМ: Указан неверный BOT_TOKEN!\n", flush=True)
        return
    except TelegramAPIError as e:
        print(f"\n⚠️ Ошибка подключения к Telegram API: {e}\n", flush=True)
        return
    except Exception as e:
        print(f"\n⚠️ Ошибка при подключении: {e}\n", flush=True)
        return

    if config.CHANNEL_ID == "@my_gift_feed_channel" or "@your_channel_username" in config.CHANNEL_ID:
        print("⚠️ ВНИМАНИЕ: Замените CHANNEL_ID в переменной на юзернейм вашего реального Telegram-канала!\n", flush=True)

    # Запускаем фоновый трекер за Звёзды и монитор блокчейна
    stars_tracker = StarsGiftTracker()
    asyncio.create_task(stars_tracker.start())
    monitor_task = asyncio.create_task(monitor_loop())

    try:
        print("🤖 Бот готов! Отправьте ему /test для проверки поста или /start для управления.", flush=True)
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        await bot.session.close()
        print("✅ Бот и монитор остановлены.", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
