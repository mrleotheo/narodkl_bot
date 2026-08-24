import os
from datetime import datetime
from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database
from config import ADMIN_ID

router = Router()

# Описываем состояние ожидания пинкода администратора
class AdminStates(StatesGroup):
    waiting_for_pin = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    # Ловим UTM-метку или ставим direct по умолчанию
    utm_source = command.args if command.args else "direct"
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Мгновенно записываем переход и UTM-метку в SQLite при запуске бота
    await database.add_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        utm_source=utm_source
    )

    # Настраиваем кнопки (оставляем только кнопку перехода к менеджеру)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")
        ]
    ])

    # Твой скорректированный и утвержденный вариант текста приветствия
    welcome_text = (
        "Здравствуйте😄\n\n"
        "✔️ Мы беремся за самые запущенные случаи (потеря 6+ зубов), от которых отказались другие.\n"
        "✔️ Работаем напрямую с ведущими клиниками и специалистами Хэйхэ, поэтому вам гарантированно помогут.\n"
        "✔️ Всё это в 2–3 раза дешевле, на более высоком технологическом уровне и значительно быстрее, чем в России.\n"
        "✔️ На выходе гарантийная карта и полное сопровождение.\n\n"
        "👉 Ваша новая уверенность и здоровье ближе, чем кажется 🤗\n"
        "...всего-то осталось сделать один шаг и\n\n"
        "👇 обратиться за бесплатной консультацией 👇"
    )

    photo_path = "welcome.jpg"

    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text=f"[Картинка welcome.jpg не найдена]\n\n{welcome_text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# Секретная команда для скачивания файла базы данных с уникальным именем
@router.message(Command("getdb"))
async def cmd_getdb(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return  # Посторонних игнорируем

    db_path = "database.db"

    if os.path.exists(db_path):
        # Получаем текущую дату и время
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        custom_filename = f"database_{current_time}.db"

        # Отправляем файл, задав ему уникальное имя на лету
        await message.reply_document(
            document=FSInputFile(db_path, filename=custom_filename),
            caption=f"📂 Актуальный файл базы данных SQLite\n🕒 Время выгрузки: {current_time}"
        )
    else:
        await message.reply("⚠️ Файл базы данных database.db пока не создан.")

# Секретная команда удаления базы данных
@router.message(Command("rmdb"))
async def cmd_rmdb(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return  # Посторонних игнорируем

    # Устанавливаем состояние ожидания пинкода
    await state.set_state(AdminStates.waiting_for_pin)
    await message.reply("⚠️ Вы ввели команду удаления базы данных, введите пинкод, чтобы совершить удаление.")

# Обработчик ввода пинкода при удалении базы
@router.message(AdminStates.waiting_for_pin)
async def process_rmdb_pin(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        await state.clear()
        return  # Посторонних игнорируем

    await state.clear()

    pin = message.text
    if not pin:
        await message.reply("❌ Ошибка ввода. Удаление отменено.")
        return

    if pin != "0123456789":
        await message.reply("❌ Неверный пинкод. Удаление базы данных отменено.")
        return

    db_path = "database.db"

    if os.path.exists(db_path):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        custom_filename = f"database_{current_time}_removed.db"

        # Сначала выгружаем финальный бэкап
        await message.reply_document(
            document=FSInputFile(db_path, filename=custom_filename),
            caption=f"📦 Финальный бэкап перед удалением\n🕒 Время удаления: {current_time}"
        )

        try:
            # Удаляем файл и инициализируем чистую базу заново [1.1.2]
            os.remove(db_path)
            await database.init_db()
            await message.reply("✅ База данных успешно удалена с сервера и инициализирована заново.")
        except Exception as e:
            await message.reply(f"❌ Произошла ошибка при физическом удалении файла: {e}")
    else:
        await message.reply("⚠️ Файл базы данных database.db не найден на сервере.")