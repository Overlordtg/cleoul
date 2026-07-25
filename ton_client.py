import re
import aiohttp
from typing import List, Dict, Any, Optional
import config
from database import db

class TonGiftFetcher:
    """
    Класс для опрашивания TonAPI / TON Indexer.
    Отслеживает ТОЛЬКО первичное улучшение (МИНТ) подарка в NFT.
    Игнорирует любые последующие переводы между кошельками и покупки на маркетплейсах.
    """
    def __init__(self, api_key: str = config.TONAPI_KEY):
        self.base_url = "https://tonapi.io/v2"
        self.headers = {}
        if api_key and api_key != "YOUR_TONAPI_KEY_HERE":
            self.headers["Authorization"] = f"Bearer {api_key}"

    def build_nft_link(self, gift_name: str, number: str) -> str:
        clean_name = gift_name.replace("'", "").replace("’", "").replace("`", "")
        words = clean_name.split()
        formatted_name = "".join(word.capitalize() for word in words)
        return f"https://t.me/nft/{formatted_name}-{number}"

    async def fetch_latest_gift_mints(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Запрашивает события из TonAPI и фильтрует ИСКЛЮЧИТЕЛЬНО первичные МИНТЫ (Улучшения).
        """
        db_gifts = db.get_all_gifts()
        
        if not db_gifts:
            raw_ids = config.get_fallback_addresses()
            items_to_check = [{"gift_id": item_id, "name": ""} for item_id in raw_ids]
        else:
            items_to_check = db_gifts

        all_parsed_gifts = []
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            for item in items_to_check:
                item_id = item["gift_id"]
                custom_name = item.get("name", "")

                if "Placeholder" in item_id or "Collection_Address" in item_id or not item_id:
                    continue

                # Запрашиваем ленту СОБЫТИЙ аккаунта/коллекции для фильтрации минтов
                events_url = f"{self.base_url}/accounts/{item_id}/events"
                params = {"limit": limit}

                try:
                    async with session.get(events_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            events = data.get("events", [])
                            
                            for ev in events:
                                for act in ev.get("actions", []):
                                    act_type = act.get("type")

                                    # 1. Прямой тип NftItemMint (Первичное чеканение/улучшение подарка)
                                    if act_type == "NftItemMint":
                                        mint_data = act.get("NftItemMint", {})
                                        nft_item = mint_data.get("nft_item", {})
                                        parsed = self._parse_item(nft_item, override_name=custom_name)
                                        if parsed:
                                            all_parsed_gifts.append(parsed)

                                    # 2. Перевод из нулевого адреса (0:000...000), что является первичным минтом
                                    elif act_type == "NftItemTransfer":
                                        t_data = act.get("NftItemTransfer", {})
                                        sender = t_data.get("sender", {}).get("address", "") if isinstance(t_data.get("sender"), dict) else ""
                                        
                                        # Проверяем, что отправителем является нулевой адрес (Минтер смарт-контракт)
                                        is_initial_mint = (not sender or sender.startswith("0:000000000") or "0000000000000000000000" in sender)
                                        
                                        if is_initial_mint:
                                            nft_item = t_data.get("nft_item", {})
                                            parsed = self._parse_item(nft_item, override_name=custom_name)
                                            if parsed:
                                                all_parsed_gifts.append(parsed)

                        elif resp.status in (400, 404):
                            # Фолбек на получение последних элементов
                            items_url = f"{self.base_url}/nfts/collections/{item_id}/items"
                            async with session.get(items_url, params={"limit": 5}, timeout=aiohttp.ClientTimeout(total=10)) as resp2:
                                if resp2.status == 200:
                                    data2 = await resp2.json()
                                    for nft in data2.get("nft_items", []):
                                        parsed = self._parse_item(nft, override_name=custom_name)
                                        if parsed:
                                            all_parsed_gifts.append(parsed)

                except Exception as e:
                    print(f"❌ [API Error] Ошибка при обработке событий коллекции {item_id}: {e}")

        return all_parsed_gifts

    def _parse_item(self, item: Dict[str, Any], override_name: str = "") -> Optional[Dict[str, Any]]:
        address = item.get("address", "")
        metadata = item.get("metadata", {})
        full_name = metadata.get("name", "")

        if not full_name and not address:
            return None

        match = re.search(r"^(.*?)\s*#(\d+)$", full_name.strip())
        if match:
            gift_name = match.group(1).strip()
            number = match.group(2).strip()
        else:
            gift_name = override_name if override_name and override_name != "Без названия" else (full_name.strip() if full_name else "Telegram Gift")
            number = str(item.get("index", item.get("id", "0")))

        telegram_link = self.build_nft_link(gift_name, number)

        # Реальные атрибуты
        raw_attributes = metadata.get("attributes", [])
        parsed_attrs = {}

        if isinstance(raw_attributes, list):
            for attr in raw_attributes:
                if isinstance(attr, dict):
                    trait_type = str(attr.get("trait_type", "") or attr.get("name", "") or attr.get("key", "")).lower()
                    val = str(attr.get("value", "") or attr.get("val", ""))
                    rarity = attr.get("rarity", attr.get("rarity_percent", attr.get("percentage", "")))
                    rarity_str = f" ({rarity}%)" if rarity and not str(rarity).endswith("%") else (f" ({rarity})" if rarity else "")
                    
                    full_val = f"{val}{rarity_str}" if val else "—"

                    if "model" in trait_type:
                        parsed_attrs["model"] = full_val
                    elif "symbol" in trait_type:
                        parsed_attrs["symbol"] = full_val
                    elif "backdrop" in trait_type or "background" in trait_type or "back" in trait_type:
                        parsed_attrs["backdrop"] = full_val
        elif isinstance(raw_attributes, dict):
            for key, val in raw_attributes.items():
                k_lower = str(key).lower()
                if "model" in k_lower:
                    parsed_attrs["model"] = str(val)
                elif "symbol" in k_lower:
                    parsed_attrs["symbol"] = str(val)
                elif "backdrop" in k_lower or "background" in k_lower:
                    parsed_attrs["backdrop"] = str(val)

        # Реальный владелец
        owner_info = item.get("owner", {})
        owner_addr = owner_info.get("address", "") if isinstance(owner_info, dict) else ""
        owner_display = owner_info.get("name", "") or owner_info.get("domain", "") if isinstance(owner_info, dict) else ""
        if not owner_display and owner_addr:
            owner_display = f"{owner_addr[:4]}...{owner_addr[-4:]}"
        elif not owner_display:
            owner_display = "Скрыт / В профиле Telegram"

        return {
            "id": address or str(item.get("index", "")),
            "gift_name": gift_name,
            "number": number,
            "link": telegram_link,
            "full_title": f"{gift_name} #{number}",
            "owner": owner_display,
            "model": parsed_attrs.get("model", "—"),
            "symbol": parsed_attrs.get("symbol", "—"),
            "backdrop": parsed_attrs.get("backdrop", "—"),
            "image_url": metadata.get("image", "")
        }
