import httpx
import logging
from config import BITRIX_WEBHOOK_URL

async def create_bitrix_lead(user_id: int, username: str | None, first_name: str | None, last_name: str | None, utm_source: str) -> bool:
    """
    Отправляет запрос в Битрикс24 для создания нового лида.
    """
    if not BITRIX_WEBHOOK_URL:
        logging.warning("BITRIX_WEBHOOK_URL не настроен. Запрос в CRM пропущен.")
        return False

    url = f"{BITRIX_WEBHOOK_URL.rstrip('/')}/crm.lead.add.json"
    
    # Собираем имя для Битрикса
    display_name = first_name or ""
    if last_name:
        display_name += f" {last_name}"
    if not display_name and username:
        display_name = username

    # Формируем тело запроса по правилам Битрикс24 REST API
    payload = {
        "fields": {
            "TITLE": f"Заявка из Telegram-бота (ID: {user_id})",
            "NAME": display_name,
            "COMMENTS": f"Профиль TG: https://t.me/{username}" if username else "Юзернейм отсутствует",
            # Стандартные UTM поля Битрикса:
            "UTM_SOURCE": "telegram",
            "UTM_MEDIUM": "bot",
            "UTM_CAMPAIGN": utm_source,  # Передаем то, откуда пришел пользователь
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}  # Оповещение в живую ленту Битрикса (опционально)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            data = response.json()
            
            if response.status_code == 200 and "result" in data:
                logging.info(f"Лид успешно создан в Битрикс24. ID Лида: {data['result']}")
                return True
            else:
                logging.error(f"Ошибка Битрикс24 API: {data.get('error_description', data)}")
                return False
    except Exception as e:
        logging.error(f"Не удалось отправить запрос в Битрикс24: {e}")
        return False