import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import database
from utils.bitrix import create_bitrix_lead
from config import ADMIN_ID

router = Router()

# Определяем шаги нашей формы
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

@router.callback_query(lambda c: c.data == "apply_lead")
async def process_apply_lead(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    user_data = await database.get_user(user_id)
    if not user_data:
        await callback_query.answer("Пожалуйста, перезапустите бота с помощью /start.", show_alert=True)
        return

    # Если уже отправлял форму
    if user_data["is_lead"] == 1:
        await callback_query.message.answer(
            "Вы уже оставили заявку! Наш менеджер свяжется с вами в ближайшее время.\n"
            "Вы также можете написать напрямую: https://t.me/narodkl_ru"
        )
        await callback_query.answer()
        return

    await callback_query.answer()
    
    # Запускаем FSM: переходим на шаг ожидания имени
    await state.set_state(Form.waiting_for_name)
    await callback_query.message.answer(
        "Отлично! Давайте оформим заявку. 📝\n\n"
        "Пожалуйста, напишите, **как к вам обращаться** (ваше имя)?"
    )

# 1. Принимаем имя
@router.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(real_name=message.text)
    
    # Переходим на шаг ожидания телефона
    await state.set_state(Form.waiting_for_phone)
    
    # Создаем клавиатуру с возможностью отправить номер телефона кнопкой
    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "Спасибо! Теперь отправьте, пожалуйста, **номер телефона**, чтобы менеджер мог с вами связаться.\n\n"
        "Вы можете нажать кнопку ниже, чтобы отправить текущий номер телефона, или написать его текстом вручную:",
        reply_markup=phone_keyboard
    )

# Обработка отмены посреди заполнения
@router.message(F.text == "❌ Отменить")
async def cancel_form(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Заполнение заявки отменено. Вы можете начать заново, нажав кнопку «Оставить заявку» в приветственном меню.",
        reply_markup=ReplyKeyboardRemove()
    )

# 2. Принимаем телефон (как контакт или текстом)
@router.message(Form.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    # Проверяем, как пришел телефон: кнопкой (contact) или текстом (text)
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text
    else:
        await message.answer("Пожалуйста, отправьте корректный номер телефона.")
        return

    # Достаем ранее сохраненное имя из FSM-хранилища
    user_data_fsm = await state.get_data()
    real_name = user_data_fsm.get("real_name")
    user_id = message.from_user.id

    # Очищаем состояние опроса и скрываем клавиатуру
    await state.clear()
    await message.answer(
        "⌛️ Секунду, регистрируем вашу заявку...", 
        reply_markup=ReplyKeyboardRemove()
    )

    # Получаем UTM-метку пользователя из локальной базы
    user_db_data = await database.get_user(user_id)
    utm_source = user_db_data["utm_source"] if user_db_data else "direct"

    # А. Создаем лид в Битрикс24 (или мокаем)
    await create_bitrix_lead(
        user_id=user_id,
        username=message.from_user.username,
        real_name=real_name,
        phone=phone,
        utm_source=utm_source
    )

    # Б. Сохраняем контакты в SQLite и помечаем как лида
    await database.save_lead_data(user_id, real_name, phone)

    # В. Отправляем подтверждение пользователю
    await message.answer(
        "🎉 Ваша заявка успешно зарегистрирована!\n\n"
        "Мы передали контакты нашему представителю, скоро с вами свяжутся.\n"
        "Если вы хотите написать менеджеру прямо сейчас, нажмите сюда: https://t.me/narodkl_ru"
    )

    # Г. Отправляем уведомление администратору (если настроен ADMIN_ID)
    if ADMIN_ID:
        try:
            admin_chat_id = int(ADMIN_ID)
            username_text = f"@{message.from_user.username}" if message.from_user.username else "отсутствует"
            
            admin_text = (
                f"🔔 **Новый лид в боте!**\n\n"
                f"👤 **Имя**: {real_name}\n"
                f"📞 **Телефон**: {phone}\n"
                f"🔗 **Юзернейм**: {username_text}\n"
                f"🆔 **ID**: `{user_id}`\n"
                f"🏷 **UTM-метка**: `{utm_source}`"
            )
            await message.bot.send_message(
                chat_id=admin_chat_id,
                text=admin_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу: {e}")