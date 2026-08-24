import os
import logging
import asyncio
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError
import database
from config import ADMIN_ID

router = Router()

# Описываем состояния для удаления базы и рассылки
class AdminStates(StatesGroup):
    waiting_for_pin = State()
    waiting_for_photo = State()
    waiting_for_text = State()
    waiting_for_button = State()
    waiting_for_confirm = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    utm_source = command.args if command.args else "direct"
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    await database.add_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        utm_source=utm_source
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")
        ]
    ])

    # Твой новый зафиксированный вариант текста приветствия
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

# Нижняя команда в меню для связи с менеджером
@router.message(Command("manager"))
async def cmd_manager(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")
        ]
    ])
    await message.answer(
        "👇 Напишите менеджеру, чтобы оставить заявку ✍️",
        reply_markup=keyboard
    )

# Секретная команда для скачивания файла базы данных
@router.message(Command("getdb"))
async def cmd_getdb(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

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

# Секретная команда удаления базы данных
@router.message(Command("rmdb"))
async def cmd_rmdb(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    await state.set_state(AdminStates.waiting_for_pin)
    await message.reply("⚠️ Вы ввели команду удаления базы данных, введите пинкод, чтобы совершить удаление.")

@router.message(AdminStates.waiting_for_pin)
async def process_rmdb_pin(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        await state.clear()
        return

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

        await message.reply_document(
            document=FSInputFile(db_path, filename=custom_filename),
            caption=f"📦 Финальный бэкап перед удалением\n🕒 Время удаления: {current_time}"
        )

        try:
            os.remove(db_path)
            await database.init_db()
            await message.reply("✅ База данных успешно удалена с сервера и инициализирована заново.")
        except Exception as e:
            await message.reply(f"❌ Произошла ошибка при физическом удалении файла: {e}")
    else:
        await message.reply("⚠️ Файл базы данных database.db не найден на сервере.")


# =========================================================
# БЛОК МАССОВОЙ РАССЫЛКИ (/sndmsg)
# =========================================================

# 1. Запуск рассылки
@router.message(Command("sndmsg"))
async def cmd_sndmsg(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    await state.set_state(AdminStates.waiting_for_photo)
    await message.reply(
        "📝 **Запуск пошагового мастера рассылки.**\n\n"
        "Отправьте картинку для сообщения, либо введите `/skip`, чтобы сделать рассылку без картинки."
    )

# 2. Принимаем фото или /skip
@router.message(AdminStates.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(photo_id=None)
    elif message.photo:
        # Берем самый крупный размер фото
        photo_id = message.photo[-1].file_id
        await state.update_data(photo_id=photo_id)
    else:
        await message.reply("Пожалуйста, отправьте фото или введите команду `/skip`.")
        return

    await state.set_state(AdminStates.waiting_for_text)
    await message.reply("✍️ Теперь введите **текст сообщения** (поддерживается стандартная HTML-разметка):")

# 3. Принимаем текст
@router.message(AdminStates.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    # Сохраняем HTML-форматирование текста
    await state.update_data(text=message.html_text)
    
    await state.set_state(AdminStates.waiting_for_button)
    await message.reply(
        "🔗 Теперь настроим кнопку.\n\n"
        "Введите текст кнопки и ссылку через вертикальную черту, например:\n"
        "`Перейти в канал | https://t.me/narodkl/46`\n\n"
        "Или отправьте `/skip`, чтобы отправить сообщение без кнопки."
    )

# 4. Принимаем кнопку или /skip, выводим предпросмотр
@router.message(AdminStates.waiting_for_button)
async def process_button(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(button=None)
    else:
        try:
            # Парсим кнопку по символу |
            btn_text, btn_url = map(str.strip, message.text.split("|"))
            if not btn_url.startswith("http"):
                raise ValueError
            await state.update_data(button={"text": btn_text, "url": btn_url})
        except Exception:
            await message.reply(
                "❌ Неверный формат кнопки. Пожалуйста, введите текст и ссылку строго через вертикальную черту, "
                "например: `Перейти в канал | https://t.me/narodkl/46` или введите `/skip`:"
            )
            return

    # Достаем все данные для генерации предпросмотра
    data = await state.get_data()
    photo_id = data.get("photo_id")
    text = data.get("text")
    button = data.get("button")

    # Формируем клавиатуру для предпросмотра
    keyboard_list = []
    if button:
        keyboard_list.append([InlineKeyboardButton(text=button["text"], url=button["url"])])
    
    # Кнопки подтверждения рассылки
    keyboard_list.append([
        InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_send"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send")
    ])
    
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_list)

    await message.reply("👀 **Предпросмотр вашего сообщения:**")

    # Показываем сообщение точно так же, как его увидят пользователи
    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=confirm_markup,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text=text,
            reply_markup=confirm_markup,
            parse_mode="HTML"
        )
    
    await state.set_state(AdminStates.waiting_for_confirm)

# 5. Обработчики кликов по кнопкам согласия/отмены
@router.callback_query(lambda c: c.data in ["confirm_send", "cancel_send"])
async def process_confirm_send(callback_query: types.CallbackQuery, state: FSMContext):
    # Проверяем права администратора на клик
    if str(callback_query.from_user.id) != str(ADMIN_ID):
        await callback_query.answer("У вас нет прав администратора.", show_alert=True)
        return

    if callback_query.data == "cancel_send":
        await state.clear()
        # Убираем кнопки из сообщения предпросмотра
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.answer("❌ Подготовка рассылки полностью отменена.")
        await callback_query.answer()
        return

    # Извлекаем данные
    data = await state.get_data()
    await state.clear()

    photo_id = data.get("photo_id")
    text = data.get("text")
    button = data.get("button")

    # Убираем кнопки подтверждения из предпросмотра, чтобы не кликнуть дважды
    await callback_query.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback_query.message.answer("⌛️ **Рассылка запущена...** Пожалуйста, подождите окончания процесса.")
    await callback_query.answer()

    # Ссылка-кнопка для пользователей
    user_markup = None
    if button:
        user_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button["text"], url=button["url"])]
        ])

    # Получаем список всех ID из базы данных
    all_users = await database.get_all_users()
    
    success_count = 0
    failed_count = 0

    for user_id in all_users:
        try:
            if photo_id:
                await callback_query.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_id,
                    caption=text,
                    reply_markup=user_markup,
                    parse_mode="HTML"
                )
            else:
                await callback_query.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=user_markup,
                    parse_mode="HTML"
                )
            success_count += 1
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            failed_count += 1
        except Exception as e:
            # Другая ошибка (например, неверный ID)
            logging.error(f"Ошибка при рассылке пользователю {user_id}: {e}")
            failed_count += 1
        
        # Микропауза между сообщениями, чтобы Telegram не забанил бота за спам
        await asyncio.sleep(0.05)

    # Меняем текст статуса на финальный отчет
    await status_msg.edit_text(
        f"📢 **Массовая рассылка успешно завершена!**\n\n"
        f"✅ Доставлено: `{success_count}`\n"
        f"❌ Не доставлено (заблокировали бота/ошибки): `{failed_count}`"
    )