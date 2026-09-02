from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database import check_and_update_blacklist

class BlacklistMiddleware(BaseMiddleware):
    """
    Промежуточный слой, который проверяет пользователя по черному списку.
    Поддерживает автопривязку ID при превентивной блокировке по нику [1.1.2].
    """
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user:
            # Проверяем по ID или по никнейму (с автопривязкой)
            if await check_and_update_blacklist(user.id, user.username):
                # Полностью игнорируем действия забаненного пользователя [1.1.2]
                return
        return await handler(event, data)