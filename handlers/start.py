import os
import json
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
from database import add_drip_post, get_all_drip_posts, delete_drip_post

router = Router()

class AdminStates(StatesGroup):
    waiting_for_pin = State()
    waiting_for_photo = State()
    waiting_for_text = State()
    waiting_for_button = State()
    waiting_for_confirm = State()

# FSM для создания автоматических постов воронки
class PostStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_text = State()
    waiting_for_buttons = State()
    waiting_for_confirm = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    utm_source = command.args if command.args else "direct"
    
    await database.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        utm_source=utm_source
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")]
    ])

    welcome_text = (
        "Если вам нужна эстетика, голливудская улыбка, виниры, то дальше можете не читать и сразу переходить в консультацию.\n\n"
        "Если есть отсутствующие зубки то, чтобы составить для вас максимально точный план, нам понадобится немного информации о вашей ситуации.\n\n"
        "Мы подготовили несколько удобных способов — выбирайте тот, который вам ближе:\n\n"
        "1. <b>Описать ситуацию своими словами</b> ✍️\n"
        "• <i>Плюс:</i> проще всего, не нужно ничего усложнять. Отлично подходит, если зубов нет совсем.\n"
        "• <i>Минус:</i> иногда в деталях легко запутаться (например, вспомнить, когда и какой зуб удалили).\n\n"
        "2. <b>Указать номера зубов по схеме</b> 🗺️\n"
        "• <i>Плюс:</i> Нам будет гораздо проще сориентироваться.\n"
        "• <i>Минус:</i> порой в нумерации случаются небольшие ошибки.\n\n"
        "3. <b>Сделать фотографии по нашей инструкции</b> 📸\n"
        "• <i>Плюс:</i> помогает разобраться в простых случаях, когда нет скрытых воспалений.\n"
        "• <i>Минус:</i> на фото не видно состояния корней.\n\n"
        "4. <b>Панорамный снимок (ОПТГ) или КТ (компьютерная томография)</b> 🔬\n"
        "• <i>Плюс:</i> Идеальный вариант — нам будет видно абсолютно всё.\n"
        "• <i>Минус:</i> Минусов просто нет.\n\n"
        "Не переживайте и не спешите сразу делать КТ! 🌿 Можно начать с самого простого варианта.\n\n"
        "А еще поделитесь, пожалуйста, вашими пожеланиями: какую задачу вы хотите решить и какому лечению отдаете предпочтение — имплантам, коронкам, мостам или съемным протезам? Мы бережно подберем лучший вариант именно для вас. ✨"
    )

    photo_path = "welcome.jpg"
    if os.path.exists(photo_path):
        await message.answer_photo(photo=FSInputFile(photo_path), caption=welcome_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text=welcome_text, reply_markup=keyboard, parse_mode="HTML")

@router.message(Command("manager"))
async def cmd_manager(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")]
    ])
    await message.answer("👇 Напишите менеджеру, чтобы оставить заявку ✍️", reply_markup=keyboard)

# --- УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ (ТОЛЬКО ДЛЯ СУПЕРАДМИНА) ---

@router.message(Command("addadmin"))
async def cmd_addadmin(message: types.Message, command: CommandObject):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    if not command.args:
        await message.reply("Используйте: `/addadmin ID_пользователя`")
        return
    try:
        admin_id = int(command.args)
        await database.add_admin(admin_id, None)
        # Динамически прописываем админу его меню
        from aiogram.types import BotCommand, BotCommandScopeChat
        admin_commands = [
            BotCommand(command="start", description="Перезапустить бота 🔄"),
            BotCommand(command="manager", description="Связаться с менеджером 👨‍💻"),
            BotCommand(command="listposts", description="Просмотр воронки ⚙️")
        ]
        await message.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        await message.reply(f"👤 Пользователь `{admin_id}` успешно назначен администратором.")
    except Exception as e:
        await message.reply(f"Ошибка при добавлении: {e}")

@router.message(Command("deladmin"))
async def cmd_deladmin(message: types.Message, command: CommandObject):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    if not command.args:
        await message.reply("Используйте: `/deladmin ID_пользователя`")
        return
    try:
        admin_id = int(command.args)
        await database.del_admin(admin_id)
        # Сбрасываем меню до стандартного
        from aiogram.types import BotCommandScopeChat
        await message.bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=admin_id))
        await message.reply(f"❌ Администратор `{admin_id}` разжалован до обычного пользователя.")
    except Exception as e:
        await message.reply(f"Ошибка при удалении: {e}")

# --- УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ (ТОЛЬКО ДЛЯ СУПЕРАДМИНА) ---

@router.message(Command("getdb"))
async def cmd_getdb(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    db_path = "database.db"
    if os.path.exists(db_path):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        await message.reply_document(FSInputFile(db_path, filename=f"database_{current_time}.db"), caption=f"📂 База SQLite\n🕒 {current_time}")
    else:
        await message.reply("⚠️ База данных пока не создана.")

@router.message(Command("rmdb"))
async def cmd_rmdb(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    await state.set_state(AdminStates.waiting_for_pin)
    await message.reply("⚠️ Введите пинкод для удаления базы данных.")

@router.message(AdminStates.waiting_for_pin)
async def process_rmdb_pin(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        await state.clear()
        return
    await state.clear()
    if message.text != "0123456789":
        await message.reply("❌ Неверный пинкод.")
        return
    db_path = "database.db"
    if os.path.exists(db_path):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        await message.reply_document(FSInputFile(db_path, filename=f"database_{current_time}_removed.db"), caption="📦 Бэкап")
        try:
            os.remove(db_path)
            await database.init_db()
            await message.reply("✅ База данных успешно удалена и пересоздана.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

# --- ЭКСТРЕННАЯ РАССЫЛКА (ТОЛЬКО ДЛЯ СУПЕРАДМИНА) ---

@router.message(Command("sndmsg"))
async def cmd_sndmsg(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    await state.set_state(AdminStates.waiting_for_photo)
    await message.reply("📝 **Экстренная рассылка.** Отправьте фото или введите `/skip`:")

@router.message(AdminStates.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(photo_id=None)
    elif message.photo:
        await state.update_data(photo_id=message.photo[-1].file_id)
    else:
        await message.reply("Отправьте фото или `/skip`.")
        return
    await state.set_state(AdminStates.waiting_for_text)
    await message.reply("✍️ Введите HTML-текст рассылки:")

@router.message(AdminStates.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.html_text)
    await state.set_state(AdminStates.waiting_for_button)
    await message.reply("🔗 Введите кнопки построчно (`Текст | Ссылка`) или `/skip`:")

@router.message(AdminStates.waiting_for_button)
async def process_button(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(buttons=None)
    else:
        try:
            btns = []
            for line in message.text.split("\n"):
                txt, url = map(str.strip, line.split("|"))
                if not url.startswith("http"):
                    raise ValueError
                btns.append({"text": txt, "url": url})
            await state.update_data(buttons=btns)
        except Exception:
            await message.reply("❌ Ошибка формата. Попробуйте еще раз или `/skip`:")
            return

    data = await state.get_data()
    photo_id = data.get("photo_id")
    text = data.get("text")
    buttons = data.get("buttons")

    keyboard_list = []
    if buttons:
        for b in buttons:
            keyboard_list.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
    keyboard_list.append([
        InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_send"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
    await message.reply("👀 **Предпросмотр рассылки:**")
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text=text, reply_markup=markup, parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_confirm)

@router.callback_query(lambda c: c.data in ["confirm_send", "cancel_send"])
async def process_confirm_send(callback_query: types.CallbackQuery, state: FSMContext):
    if str(callback_query.from_user.id) != str(ADMIN_ID):
        await callback_query.answer("Доступ только суперадмину.", show_alert=True)
        return

    if callback_query.data == "cancel_send":
        await state.clear()
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.answer("❌ Рассылка отменена.")
        await callback_query.answer()
        return

    data = await state.get_data()
    await state.clear()

    photo_id = data.get("photo_id")
    text = data.get("text")
    buttons = data.get("buttons")

    await callback_query.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback_query.message.answer("⌛️ Рассылка запущена...")
    await callback_query.answer()

    markup = None
    if buttons:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=b["text"], url=b["url"])] for b in buttons
        ])

    all_users = await database.get_all_users()
    success, failed = 0, 0

    for user_id in all_users:
        try:
            if photo_id:
                await callback_query.bot.send_photo(chat_id=user_id, photo=photo_id, caption=text, reply_markup=markup, parse_mode="HTML")
            else:
                await callback_query.bot.send_message(chat_id=user_id, text=text, reply_markup=markup, parse_mode="HTML")
            success += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(f"📢 **Рассылка завершена!**\n\n✅ Доставлено: `{success}`\n❌ Заблокировано: `{failed}`")


# --- СОЗДАНИЕ ПОСТОВ ВОРОНКИ (ТОЛЬКО ДЛЯ СУПЕРАДМИНА) ---

@router.message(Command("addpost"))
async def cmd_addpost(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    await state.set_state(PostStates.waiting_for_photo)
    await message.reply("📝 **Создание авто-поста воронки.** Отправьте картинку или `/skip`:")

@router.message(PostStates.waiting_for_photo)
async def process_post_photo(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(photo_id=None)
    elif message.photo:
        await state.update_data(photo_id=message.photo[-1].file_id)
    else:
        await message.reply("Отправьте фото или `/skip`:")
        return
    await state.set_state(PostStates.waiting_for_text)
    await message.reply("✍️ Введите HTML-текст авто-поста:")

@router.message(PostStates.waiting_for_text)
async def process_post_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.html_text)
    await state.set_state(PostStates.waiting_for_buttons)
    await message.reply("🔗 Введите кнопки построчно (`Текст | Ссылка`) или `/skip`:")

@router.message(PostStates.waiting_for_buttons)
async def process_post_buttons(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(buttons=None)
    else:
        try:
            btns = []
            for line in message.text.split("\n"):
                txt, url = map(str.strip, line.split("|"))
                if not url.startswith("http"):
                    raise ValueError
                btns.append({"text": txt, "url": url})
            await state.update_data(buttons=btns)
        except Exception:
            await message.reply("❌ Ошибка формата кнопки. Попробуйте еще раз или `/skip`:")
            return

    data = await state.get_data()
    photo_id = data.get("photo_id")
    text = data.get("text")
    buttons = data.get("buttons")

    keyboard_list = []
    if buttons:
        for b in buttons:
            keyboard_list.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
    keyboard_list.append([
        InlineKeyboardButton(text="✅ Сохранить шаг воронки", callback_data="save_post"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_list)
    await message.reply("👀 **Предпросмотр авто-поста воронки:**")
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text=text, reply_markup=markup, parse_mode="HTML")
    await state.set_state(PostStates.waiting_for_confirm)

@router.callback_query(lambda c: c.data in ["save_post", "cancel_post"])
async def process_confirm_post(callback_query: types.CallbackQuery, state: FSMContext):
    if str(callback_query.from_user.id) != str(ADMIN_ID):
        await callback_query.answer("Доступ только суперадмину.", show_alert=True)
        return

    if callback_query.data == "cancel_post":
        await state.clear()
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.answer("❌ Создание авто-поста отменено.")
        await callback_query.answer()
        return

    data = await state.get_data()
    await state.clear()

    photo_id = data.get("photo_id")
    text = data.get("text")
    buttons = data.get("buttons")

    await callback_query.message.edit_reply_markup(reply_markup=None)
    
    # Сохраняем пост в базу
    await add_drip_post(photo_id, text, buttons)
    
    await callback_query.message.answer("✅ Шаг прогрева успешно добавлен в воронку!")
    await callback_query.answer()


# --- ЛИСТИНГ И УДАЛЕНИЕ ШАГОВ ВОРОНКИ (ПРОСМОТР ДЛЯ АДМИНОВ, ИЗМЕНЕНИЯ ТОЛЬКО СУПЕРАДМИНУ) ---

@router.message(Command("listposts"))
async def cmd_listposts(message: types.Message):
    # Проверяем, админ ли (или суперадмин)
    is_user_admin = await database.is_admin(message.from_user.id)
    is_superadmin = str(message.from_user.id) == str(ADMIN_ID)
    
    if not is_user_admin and not is_superadmin:
        return  # Обычные пользователи команду не видят

    posts = await get_all_drip_posts()
    if not posts:
        await message.reply("⚠️ Воронка пуста. Добавьте посты через команду /addpost.")
        return

    await message.reply(f"⚙️ **Текущая прогревочная воронка (Всего шагов: {len(posts)}):**")

    for post in posts:
        keyboard_list = []
        if post["buttons"]:
            for b in post["buttons"]:
                keyboard_list.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
        
        # ЕСЛИ ЗАПРОСИЛ СУПЕРАДМИН: добавляем кнопку удаления!
        # Обычные админы кнопку удаления не видят и удалить шаг не смогут [1.1.2]
        if is_superadmin:
            keyboard_list.append([
                InlineKeyboardButton(text=f"❌ Удалить Шаг {post['step_number']}", callback_data=f"del_step_{post['step_number']}")
            ])
            
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard_list) if keyboard_list else None
        header_text = f"📌 **ШАГ №{post['step_number']}**\n\n"
        
        if post["photo_id"]:
            await message.answer_photo(photo=post["photo_id"], caption=f"{header_text}{post['text']}", reply_markup=markup, parse_mode="HTML")
        else:
            await message.answer(text=f"{header_text}{post['text']}", reply_markup=markup, parse_mode="HTML")

@router.callback_query(lambda c: c.data.startswith("del_step_"))
async def process_del_step(callback_query: types.CallbackQuery):
    # Удалять может ТОЛЬКО суперадмин! [1.1.2]
    if str(callback_query.from_user.id) != str(ADMIN_ID):
        await callback_query.answer("Удалять шаги может только суперадминистратор!", show_alert=True)
        return

    step_to_delete = int(callback_query.data.replace("del_step_", ""))
    
    # Удаляем шаг и автоматически сдвигаем остальные в БД [1.1.2]
    await delete_drip_post(step_to_delete)
    
    await callback_query.message.answer(f"✅ Шаг №{step_to_delete} успешно удален. Последующие шаги сдвинуты назад.")
    # Стираем кнопки, чтобы не кликнуть дважды
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.answer()


# --- СПИДРАН ТЕСТ ВОРОНКИ (ТОЛЬКО ДЛЯ СУПЕРАДМИНА) ---

@router.message(Command("speedrun"))
async def cmd_speedrun(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    posts = await get_all_drip_posts()
    if not posts:
        await message.reply("⚠️ Воронка пуста. Сначала добавьте шаги через /addpost.")
        return

    await message.reply("⚡️ **Запуск спидрана воронки для вас!**\n\nВсе шаги прогрева будут приходить один за другим с паузой в 5 секунд:")

    for post in posts:
        keyboard = None
        if post["buttons"]:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=b["text"], url=b["url"])] for b in post["buttons"]
            ])
            
        header_text = f"⚡️ *[СПИДРАН]* Шаг №{post['step_number']}\n\n"
        
        if post["photo_id"]:
            await message.answer_photo(photo=post["photo_id"], caption=f"{header_text}{post['text']}", reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text=f"{header_text}{post['text']}", reply_markup=keyboard, parse_mode="HTML")
            
        await asyncio.sleep(5)

    await message.answer("✅ Тестовый спидран всей цепочки воронки успешно завершен!")