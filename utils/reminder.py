import asyncio
import logging
import json
import aiosqlite
from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError
from database import DB_PATH, get_drip_post

async def send_reminders(bot: Bot):
    """Отправляет заготовленные посты воронки каждые 24 часа."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Шаг 1. Находим пользователей, у которых прошло более 24 часов со старта и нет записей в прогрессе воронки [1.1.2]
        async with db.execute("""
            SELECT id FROM users 
            WHERE id NOT IN (SELECT user_id FROM user_drip_status)
            AND datetime(created_at) <= datetime('now', '-1 day')
        """) as cursor:
            step1_users = await cursor.fetchall()

        # Шаг N. Находим пользователей, у которых прошло более 24 часов с момента последней отправки [1.1.2]
        async with db.execute("""
            SELECT user_id, last_post_step FROM user_drip_status
            WHERE datetime(last_sent_at) <= datetime('now', '-1 day')
        """) as cursor:
            step_n_users = await cursor.fetchall()

    # --- Обработка Шага 1 ---
    if step1_users:
        post = await get_drip_post(1)
        if post:
            for (user_id,) in step1_users:
                await send_post_to_user(bot, user_id, post, 1)

    # --- Обработка Шагов N ---
    for user_id, last_step in step_n_users:
        next_step = last_step + 1
        post = await get_drip_post(next_step)
        if post:
            await send_post_to_user(bot, user_id, post, next_step)

async def send_post_to_user(bot: Bot, user_id: int, post: dict, step: int):
    """Вспомогательная функция отправки конкретного шага пользователю."""
    keyboard = None
    if post["buttons"]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=b["text"], url=b["url"])] for b in post["buttons"]
        ])

    try:
        if post["photo_id"]:
            await bot.send_photo(
                chat_id=user_id,
                photo=post["photo_id"],
                caption=post["text"],
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=post["text"],
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        logging.info(f"Воронка: Шаг {step} успешно отправлен пользователю {user_id}")
    except TelegramForbiddenError:
        logging.warning(f"Воронка: Пользователь {user_id} заблокировал бота. Отправка отменена.")
    except Exception as e:
        logging.error(f"Воронка: Ошибка отправки Шага {step} пользователю {user_id}: {e}")

    # Записываем прогресс в базу
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_drip_status (user_id, last_post_step, last_sent_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                last_post_step = excluded.last_post_step,
                last_sent_at = CURRENT_TIMESTAMP
        """, (user_id, step))
        await db.commit()