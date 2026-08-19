import httpx
import logging
from config import BITRIX_WEBHOOK_URL

async def create_bitrix_lead(user_id: int, username: str | None, real_name: str, phone: str, utm_source: str) -> bool:
    """
    Отправляет запрос в Битрикс24 для создания нового лида с именем, телефоном и UTM-меткой.
    """
    if not BITRIX_WEBHOOK_URL:
        logging.warning("BITRIX_WEBHOOK_URL не настроен. Запрос пропущен.")
        return False

    base_url = BITRIX_WEBHOOK_URL.rstrip('/')
    url = f"{base_url}/crm.lead.add.json"

    # Формируем тело запроса
    payload = {
        "fields": {
            "TITLE": f"Заявка из бота: {real_name}",
            "NAME": real_name,
            
            # Структура для передачи телефона в CRM
            "PHONE": [
                {
                    "VALUE": phone,
                    "VALUE_TYPE": "WORK"
                }
            ],
            "COMMENTS": f"Профиль TG: https://t.me/{username}\nID пользователя: {user_id}" if username else f"ID пользователя: {user_id}",
            
            # UTM-метки
            "UTM_SOURCE": "telegram",
            "UTM_MEDIUM": "bot",
            "UTM_CAMPAIGN": utm_source,
        },
        "params": {
            "REGISTER_SONET_EVENT": "Y"
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            data = response.json()
            
            if response.status_code == 200 and "result" in data:
                logging.info(f"✅ Лид успешно создан в Битрикс24. ID: {data['result']}")
                return True
            else:
                error_msg = data.get("error_description") or data.get("error") or data
                logging.error(f"❌ Ошибка Битрикс24 API: {error_msg}")
                return False
    except Exception as e:
        logging.error(f"❌ Не удалось отправить запрос в Битрикс24: {e}")
        return False