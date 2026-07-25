from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import db
from bot_publisher import TelegramPublisher
import config

router = Router()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    if not config.ADMIN_IDS:
        return True  # Если ADMIN_IDS не задан в .env, разрешаем всем для удобства настройки
    return user_id in config.ADMIN_IDS

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Генерирует инлайн-клавиатуру главной панели админки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Список подарков", callback_data="admin_list_gifts"),
                InlineKeyboardButton(text="➕ Добавить подарок", callback_data="admin_add_help")
            ],
            [
                InlineKeyboardButton(text="🧪 Тест карточки в канал", callback_data="admin_test_post"),
                InlineKeyboardButton(text="🔄 Обновить меню", callback_data="admin_refresh")
            ]
        ]
    )

@router.message(Command("start", "admin"))
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к административной панели.")
        return

    gifts = db.get_all_gifts()
    text = (
        "⚙️ <b>Панель управления монитором подарков</b>\n\n"
        f"📊 Сейчас в базе отслеживается: <b>{len(gifts)}</b> подарков/коллекций.\n\n"
        "<b>Команды бота:</b>\n"
        "• <code>/test</code> — проверить отправку тестовой карточки Restless Jar в канал\n"
        "• <code>/add &lt;ID&gt; [Название]</code> — добавить подарок/коллекцию\n"
        "• <code>/list</code> — просмотреть список отслеживаемых\n"
        "• <code>/del &lt;ID&gt;</code> — удалить подарок из базы"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_keyboard())

@router.message(Command("test"))
async def cmd_test(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer("🔄 Отправка тестовой карточки Restless Jar в ваш Telegram-канал...")
    publisher = TelegramPublisher()
    test_gift = {
        "id": "test_mint_90476",
        "gift_name": "Restless Jar",
        "number": "90476",
        "link": "https://t.me/nft/RestlessJar-90476",
        "full_title": "Restless Jar #90476",
        "owner": "EQD...a1b2",
        "model": "Neon Amber (0.8%)",
        "symbol": "Lightning (0.3%)",
        "backdrop": "Dark Obsidian (1.2%)"
    }
    success = await publisher.send_gift_notification(test_gift)
    if success:
        await message.answer(
            f"✅ <b>Тестовая карточка Restless Jar #90476 успешно доставлена в канал {config.CHANNEL_ID}!</b>\n\n"
            f"Ссылка: https://t.me/nft/RestlessJar-90476",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>Не удалось отправить карточку в {config.CHANNEL_ID}.</b>\n\n"
            f"Убедитесь, что бот добавлен в канал в качестве администратора.",
            parse_mode="HTML"
        )

@router.message(Command("add"))
async def cmd_add_gift(message: Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer(
            "⚠️ <b>Формат команды:</b>\n"
            "<code>/add &lt;ID_или_Адрес&gt; [Название]</code>\n\n"
            "Пример: <code>/add 5886756255493523118 Restless Jar</code>",
            parse_mode="HTML"
        )
        return

    gift_id = args[1].strip()
    name = args[2].strip() if len(args) > 2 else "Подарок " + gift_id[:8]

    if db.add_gift(gift_id, name):
        await message.answer(
            f"✅ <b>Подарок успешно добавлен!</b>\n\n"
            f"🆔 <b>ID / Адрес:</b> <code>{gift_id}</code>\n"
            f"📌 <b>Название:</b> {name}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Ошибка при добавлении подарка в базу данных.")

@router.message(Command("list"))
async def cmd_list_gifts(message: Message):
    if not is_admin(message.from_user.id):
        return

    gifts = db.get_all_gifts()
    if not gifts:
        await message.answer("📭 База подарков пуста. Добавьте первый подарок командой <code>/add &lt;ID&gt; [Название]</code>", parse_mode="HTML")
        return

    text = f"📋 <b>Список отслеживаемых подарков ({len(gifts)}):</b>\n\n"
    keyboard_buttons = []

    for g in gifts:
        text += f"• <b>{g['name']}</b>\n  └ ID: <code>{g['gift_id']}</code>\n"
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"❌ Удалить {g['name'][:15]}", callback_data=f"del_gift:{g['gift_id']}")
        ])

    keyboard_buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_list_gifts")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(text, parse_mode="HTML", reply_markup=markup)

@router.message(Command("del"))
async def cmd_del_gift(message: Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Укажите ID подарка: <code>/del &lt;ID&gt;</code>", parse_mode="HTML")
        return

    gift_id = args[1].strip()
    if db.remove_gift(gift_id):
        await message.answer(f"🗑 Подарок <code>{gift_id}</code> удален из мониторинга.", parse_mode="HTML")
    else:
        await message.answer("❌ Не удалось удалить подарок.", parse_mode="HTML")

@router.callback_query(F.data == "admin_list_gifts")
async def cb_list_gifts(call: CallbackQuery):
    gifts = db.get_all_gifts()
    if not gifts:
        await call.message.edit_text("📭 База подарков пуста.", reply_markup=get_admin_keyboard())
        await call.answer()
        return

    text = f"📋 <b>Список отслеживаемых подарков ({len(gifts)}):</b>\n\n"
    keyboard_buttons = []

    for g in gifts:
        text += f"• <b>{g['name']}</b> (<code>{g['gift_id']}</code>)\n"
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"❌ Удалить {g['name'][:15]}", callback_data=f"del_gift:{g['gift_id']}")
        ])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_refresh")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await call.answer()

@router.callback_query(F.data.startswith("del_gift:"))
async def cb_delete_gift(call: CallbackQuery):
    gift_id = call.data.split(":", 1)[1]
    if db.remove_gift(gift_id):
        await call.answer(f"🗑 Удалено: {gift_id}")
        await cb_list_gifts(call)
    else:
        await call.answer("❌ Ошибка удаления")

@router.callback_query(F.data == "admin_test_post")
async def cb_test_post(call: CallbackQuery):
    await call.answer("🔄 Тестирование...")
    publisher = TelegramPublisher()
    test_gift = {
        "id": "test_mint_90476",
        "gift_name": "Restless Jar",
        "number": "90476",
        "link": "https://t.me/nft/RestlessJar-90476",
        "full_title": "Restless Jar #90476",
        "owner": "EQD...a1b2",
        "model": "Neon Amber (0.8%)",
        "symbol": "Lightning (0.3%)",
        "backdrop": "Dark Obsidian (1.2%)"
    }
    success = await publisher.send_gift_notification(test_gift)
    if success:
        await call.message.answer(f"✅ Тестовая карточка Restless Jar #90476 успешно доставлена в ваш канал {config.CHANNEL_ID}!")
    else:
        await call.message.answer(f"❌ Ошибка отправки карточки в канал {config.CHANNEL_ID}.")

@router.callback_query(F.data == "admin_add_help")
async def cb_add_help(call: CallbackQuery):
    text = (
        "➕ <b>Как добавить подарок в базу:</b>\n\n"
        "Отправьте команду:\n"
        "<code>/add &lt;ID_или_Адрес&gt; [Название]</code>\n\n"
        "<b>Примеры:</b>\n"
        "<code>/add 5886756255493523118 Restless Jar</code>\n"
        "<code>/add EQCA14o1-4Jzv-2y_0DBP Durov's Cap</code>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await call.answer()

@router.callback_query(F.data == "admin_refresh")
async def cb_refresh(call: CallbackQuery):
    gifts = db.get_all_gifts()
    text = (
        "⚙️ <b>Панель управления монитором подарков</b>\n\n"
        f"📊 Сейчас в базе отслеживается: <b>{len(gifts)}</b> подарков/коллекций."
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await call.answer()
