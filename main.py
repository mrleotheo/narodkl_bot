import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import database

# Импортируем наши обработчики
from handlers import start, callback

# Настройка логирования в консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

async def main():
    # Инициализируем БД
    await database.init_db()
    logging.info("База данных успешно инициализирована.")

    # Инициализируем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры обработчиков
    dp.include_router(start.router)
    dp.include_router(callback.router)

    logging.info("Бот запущен в режиме Long Polling...")
    
    try:
        # Пропускаем накопившиеся сообщения, пока бот был оффлайн
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")