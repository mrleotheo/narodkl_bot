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

    # Настраиваем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Перейти в группу 💬", url="https://t.me/narodkl"),
            InlineKeyboardButton(text="Перейти в канал 📢", url="https://t.me/narodkl_ch")
        ],
        [
            InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")
        ]
    ])

    # Твой скорректированный текст приветствия
    welcome_text = (
        "Привет!✌️\n\nНаша команда сотрудничает с лучшими клиниками в г. Хэйхэ , Китай. "
        "А по некоторым вопросам и с конкретными специалистами, чтобы гарантированно помочь вам.\n\n"
        "Уже более 9 лет мы помогаем пациентам даже с самыми запущенными случаями "
        "(например, когда отсутствует 6 и более зубов) кардинально решить проблему. "
        "Около 93% наших клиентов рекомендуют нас своим близким и друзьям. А остальные просто предпочитают не афишировать лечение😉\n\n"
        "💴 Стоматологические услуги в Китае стоят в 2–4 раза дешевле, чем в России, а сам процесс лечения проходит гораздо быстрее, "
        "что критически важно, когда восстановить зубы нужно срочно⏳\n\n"
        "👇 Напишите менеджеру, чтобы оставить заявку ✍️"
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
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        custom_filename = f"database_{current_time}.db"

        await message.reply_document(
            document=FSInputFile(db_path, filename=custom_filename),
            caption=f"📂 Актуальный файл базы данных SQLite\n🕒 Время выгрузки: {current_time}"
        )
    else:
        await message.reply("⚠️ Файл базы данных database.db пока не создан.")

# 1. Секретная команда удаления базы данных
@router.message(Command("rmdb"))
async def cmd_rmdb(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return  # Посторонних игнорируем

    # Устанавливаем состояние ожидания пинкода
    await state.set_state(AdminStates.waiting_for_pin)
    await message.reply("⚠️ Вы ввели команду удаления базы данных, введите пинкод, чтобы совершить удаление.")

# 2. Обработчик ввода пинкода
@router.message(AdminStates.waiting_for_pin)
async def process_rmdb_pin(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        await state.clear()
        return  # Посторонних игнорируем

    # Очищаем состояние в любом случае (чтобы сбросить опрос)
    await state.clear()

    pin = message.text
    if not pin:
        await message.reply("❌ Ошибка ввода. Удаление отменено.")
        return

    # Проверяем пинкод
    if pin != "0123456789":
        await message.reply("❌ Неверный пинкод. Удаление базы данных отменено.")
        return

    db_path = "database.db"

    if os.path.exists(db_path):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        custom_filename = f"database_{current_time}_removed.db"

        # Шаг А. Сначала выгружаем базу в виде бэкапа с суффиксом _removed
        await message.reply_document(
            document=FSInputFile(db_path, filename=custom_filename),
            caption=f"📦 Финальный бэкап перед удалением\n🕒 Время удаления: {current_time}"
        )

        # Шаг Б. Физически удаляем файл базы и пересоздаем структуру [1.1.2]
        try:
            os.remove(db_path)
            # Мгновенно инициализируем чистую базу заново [1.1.2]
            await database.init_db()
            await message.reply("✅ База данных успешно удалена с сервера и инициализирована заново.")
        except Exception as e:
            await message.reply(f"❌ Произошла ошибка при физическом удалении файла: {e}")
    else:
        await message.reply("⚠️ Файл базы данных database.db не найден на сервере.")