import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
import database
from utils.reminder import send_reminders

# Импортируем наши обработчики
from handlers import start, callback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

async def set_commands(bot: Bot):
    """Устанавливает нижнее меню команд в левом углу у пользователя."""
    commands = [
        BotCommand(command="start", description="Перезапустить бота 🔄"),
        BotCommand(command="manager", description="Связаться с менеджером 👨‍💻")
    ]
    await bot.set_my_commands(commands)

async def check_reminders_loop(bot: Bot):
    """Фоновый асинхронный цикл для автоматической проверки напоминаний раз в час."""
    while True:
        try:
            await send_reminders(bot)
        except Exception as e:
            logging.error(f"Ошибка в цикле напоминаний: {e}")
        # Проверяем базу каждый час (3600 секунд)
        await asyncio.sleep(3600)

async def main():
    # Инициализируем БД и проводим миграцию
    await database.init_db()
    logging.info("База данных успешно инициализирована.")

    # Инициализируем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Устанавливаем нижнее меню команд
    await set_commands(bot)
    logging.info("Нижнее меню команд успешно установлено.")

    # Подключаем роутеры обработчиков
    dp.include_router(start.router)
    dp.include_router(callback.router)

    # Запускаем фоновый цикл рассылки напоминаний в параллельной задаче (не блокируя бота) [1.1.2]
    asyncio.create_task(check_reminders_loop(bot))
    logging.info("Фоновый планировщик напоминаний запущен.")

    logging.info("Бот запущен в режиме Long Polling...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")