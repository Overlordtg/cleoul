import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Токен вашего Telegram бота (получить в @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Юзернейм или ID вашего канала
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel_username")

# Ключ TonAPI (получить бесплатно на https://tonconsole.com)
TONAPI_KEY = os.getenv("TONAPI_KEY", "")

# Данные для подключения к Supabase PostgreSQL
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Список Telegram ID администраторов через запятую
_raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [
    int(aid.strip()) for aid in _raw_admin_ids.split(",") if aid.strip().isdigit()
]

# Интервал проверки новых минтов в секундах
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

# Резервные адреса из .env (если БД пуста)
_raw_addresses = os.getenv("GIFTS_COLLECTION_ADDRESS", "")

def get_fallback_addresses() -> List[str]:
    """Возвращает резервные адреса из .env."""
    return [addr.strip() for addr in _raw_addresses.split(",") if addr.strip()]
