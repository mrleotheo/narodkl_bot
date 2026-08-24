import asyncio
import logging
import os
import aiosqlite
from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramForbiddenError
from database import DB_PATH

async def send_reminders(bot: Bot):
    """Проверяет базу и отправляет напоминания пользователям спустя 3 дня."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Находим пользователей, у которых reminder_sent = 0 и прошло более 3 дней с момента старта
        async with db.execute("""
            SELECT id, utm_source FROM users 
            WHERE reminder_sent = 0 
            AND datetime(created_at) <= datetime('now', '-3 days')
        """) as cursor:
            users_to_remind = await cursor.fetchall()

        if not users_to_remind:
            return

        logging.info(f"Найдено {len(users_to_remind)} пользователей для отправки напоминания.")

        for user_id, utm_source in users_to_remind:
            try:
                # Кнопка перехода в канал
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Перейти в канал 📢", url="https://t.me/narodkl/46")
                    ]
                ])

                reminder_text = (
                    "Здравствуйте! Понимаем, что здоровье зубов — тема деликатная, и делать первый шаг всегда волнительно😌\n\n"
                    "Поэтому приглашаем вас в наш канал: там много полезной информации для спокойного погружения в тему. "
                    "Подписывайтесь, а мы просто будем рядом, чтобы ответить на ваши вопросы❤️"
                )

                # Отправляем сообщение
                await bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                logging.info(f"Напоминание успешно отправлено пользователю {user_id}")

            except TelegramForbiddenError:
                # Если пользователь заблокировал бота, мы не сможем отправить ему сообщение.
                # Просто помечаем его в базе, чтобы больше не пытаться слать ему запросы.
                logging.warning(f"Пользователь {user_id} заблокировал бота.")
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

            # В любом случае помечаем в базе, что напоминание обработано (чтобы не слать повторно) [1.1.2]
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET reminder_sent = 1 WHERE id = ?", (user_id,))
                await db.commit()
            
            # Небольшая пауза между отправками, чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.05)