import json
import logging
from datetime import datetime

async def create_bitrix_lead(user_id: int, username: str | None, first_name: str | None, last_name: str | None, utm_source: str) -> bool:
    """
    Имитирует отправку лида в Битрикс24, записывая структурированные данные в локальный файл.
    """
    # Собираем имя для логов
    display_name = first_name or ""
    if last_name:
        display_name += f" {last_name}"
    if not display_name and username:
        display_name = username

    # Формируем точно такое же тело запроса, какое пойдет в Битрикс24
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "crm_method": "crm.lead.add",
        "fields": {
            "TITLE": f"Заявка из Telegram-бота (ID: {user_id})",
            "NAME": display_name,
            "COMMENTS": f"Профиль TG: https://t.me/{username}" if username else "Юзернейм отсутствует",
            "UTM_SOURCE": "telegram",
            "UTM_MEDIUM": "bot",
            "UTM_CAMPAIGN": utm_source,  # Наша UTM-метка из SQLite
        }
    }

    try:
        # Дописываем структуру в файл mock_leads.json
        with open("mock_leads.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        
        logging.info(f"✅ [MOCK CRM] Заявка успешно записана в mock_leads.json для пользователя {display_name} (UTM: {utm_source})")
        return True
    except Exception as e:
        logging.error(f"Не удалось записать тестовый лид в файл: {e}")
        return False