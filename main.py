import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeChat
from config import BOT_TOKEN, ADMIN_ID
import database
from utils.reminder import send_reminders

# Импортируем наши обработчики
from handlers import start, callback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

async def set_dynamic_commands(bot: Bot):
    """Устанавливает индивидуальные меню команд для пользователей, админов и суперадмина."""
    # 1. Меню по умолчанию для обычных пользователей
    default_commands = [
        BotCommand(command="start", description="Перезапустить бота 🔄"),
        BotCommand(command="manager", description="Связаться с менеджером 👨‍💻")
    ]
    await bot.set_my_commands(default_commands)

    # 2. Меню для суперадминистратора (тебя) - имеет все команды управления воронкой
    superadmin_commands = [
        BotCommand(command="start", description="Перезапустить бота 🔄"),
        BotCommand(command="manager", description="Связаться с менеджером 👨‍💻"),
        BotCommand(command="addpost", description="Создать шаг прогрева 📝"),
        BotCommand(command="listposts", description="Настройка воронки ⚙️"),
        BotCommand(command="addadmin", description="Назначить админа 👤"),
        BotCommand(command="deladmin", description="Разжаловать админа ❌"),
        BotCommand(command="sndmsg", description="Массовая рассылка 📢"),
        BotCommand(command="getdb", description="Скачать базу данных 📂"),
        BotCommand(command="rmdb", description="Очистить базу данных ⚠️"),
        BotCommand(command="speedrun", description="Тест воронки ⚡️")
    ]
    try:
        await bot.set_my_commands(superadmin_commands, scope=BotCommandScopeChat(chat_id=int(ADMIN_ID)))
        logging.info(f"Динамическое меню суперадминистратора {ADMIN_ID} установлено.")
    except Exception as e:
        logging.error(f"Не удалось установить меню суперадминистратора: {e}")

    # 3. Меню для обычных администраторов (из базы данных)
    admin_commands = [
        BotCommand(command="start", description="Перезапустить бота 🔄"),
        BotCommand(command="manager", description="Связаться с менеджером 👨‍💻"),
        BotCommand(command="listposts", description="Просмотр воронки ⚙️")
    ]
    try:
        admins = await database.get_all_admins()
        for admin_id in admins:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        logging.info(f"Меню администраторов установлено для {len(admins)} пользователей.")
    except Exception as e:
        logging.error(f"Ошибка при установке меню администраторов: {e}")

async def check_reminders_loop(bot: Bot):
    """Фоновый асинхронный цикл для автоматической проверки напоминаний раз в 30 минут."""
    while True:
        try:
            await send_reminders(bot)
        except Exception as e:
            logging.error(f"Ошибка в планировщике воронки: {e}")
        # Проверяем базу каждые 30 минут (1800 секунд)
        await asyncio.sleep(1800)

async def main():
    # Инициализируем БД
    await database.init_db()
    logging.info("База данных успешно инициализирована.")

    # Инициализируем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Устанавливаем динамические меню команд
    await set_dynamic_commands(bot)

    # Подключаем роутеры обработчиков
    dp.include_router(start.router)
    dp.include_router(callback.router)

    # Запускаем фоновый цикл рассылки воронки в параллельной задаче
    asyncio.create_task(check_reminders_loop(bot))
    logging.info("Планировщик прогревочной воронки успешно запущен.")

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