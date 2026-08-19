import httpx
import logging
from config import BITRIX_WEBHOOK_URL

# Токен безопасности (должен совпадать с $security_token в PHP файле)
PROXY_SECURITY_TOKEN = "super_secret_token_123456"

async def create_bitrix_lead(user_id: int, username: str | None, real_name: str, phone: str, utm_source: str) -> bool:
    """
    Отправляет запрос на прокси-сайт в РФ, который пересылает его в Битрикс24.
    """
    if not BITRIX_WEBHOOK_URL:
        logging.warning("BITRIX_WEBHOOK_URL не настроен в .env!")
        return False

    # В качестве URL мы теперь используем адрес нашего PHP-скрипта на сайте:
    # например, BITRIX_WEBHOOK_URL = https://твой-сайт.ру/bx_proxy.php
    url = BITRIX_WEBHOOK_URL

    payload = {
        "fields": {
            "TITLE": f"Заявка из бота: {real_name}",
            "NAME": real_name,
            "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
            "COMMENTS": f"Профиль TG: https://t.me/{username}\nID пользователя: {user_id}" if username else f"ID пользователя: {user_id}",
            "UTM_SOURCE": "telegram",
            "UTM_MEDIUM": "bot",
            "UTM_CAMPAIGN": utm_source,
        }
    }

    # Передаем секретный токен в заголовках, чтобы сайт впустил бота
    headers = {
        "Content-Type": "application/json",
        "X-Proxy-Token": PROXY_SECURITY_TOKEN
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            data = response.json()
            
            if response.status_code == 200 and "result" in data:
                logging.info(f"✅ Лид успешно создан в Битрикс24 через прокси-сайт. ID: {data['result']}")
                return True
            else:
                error_msg = data.get("error_description") or data.get("error") or data
                logging.error(f"❌ Ошибка прокси-сайта/Битрикс24: {error_msg}")
                return False
    except Exception as e:
        logging.error(f"❌ Не удалось отправить запрос через прокси-сайт: {e}")
        return False