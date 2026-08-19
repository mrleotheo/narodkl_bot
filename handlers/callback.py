# =========================================================
# ВРЕМЕННО ЗАКОНСЕРВИРОВАНО (ВЫГРУЖАЕМ ПУСТОЙ РОУТЕР)
# =========================================================

from aiogram import Router

router = Router()

"""
# Ниже находится законсервированный код для сбора заявок (FSM)
# Мы сможем активировать его в любой момент, просто убрав тройные кавычки сверху и снизу.

import logging
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import database
from utils.bitrix import create_bitrix_lead
from config import ADMIN_ID

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

    if user_data["is_lead"] == 1:
        await callback_query.message.answer(
            "Вы уже оставили заявку! Наш менеджер свяжется с вами в ближайшее время.\n"
            "Вы также можете написать напрямую: https://t.me/narodkl_ru"
        )
        await callback_query.answer()
        return

    await callback_query.answer()
    await state.set_state(Form.waiting_for_name)
    await callback_query.message.answer(
        "Отлично! Давайте оформим заявку. 📝\n\n"
        "Пожалуйста, напишите, **как к вам обращаться** (ваше имя)?"
    )

@router.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(real_name=message.text)
    await state.set_state(Form.waiting_for_phone)
    
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

@router.message(F.text == "❌ Отменить")
async def cancel_form(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Заполнение заявки отменено.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Form.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text
    else:
        await message.answer("Пожалуйста, отправьте корректный номер телефона.")
        return

    user_data_fsm = await state.get_data()
    real_name = user_data_fsm.get("real_name")
    user_id = message.from_user.id

    await state.clear()
    await message.answer(
        "⌛️ Секунду, регистрируем вашу заявку...", 
        reply_markup=ReplyKeyboardRemove()
    )

    user_db_data = await database.get_user(user_id)
    utm_source = user_db_data["utm_source"] if user_db_data else "direct"

    await create_bitrix_lead(
        user_id=user_id,
        username=message.from_user.username,
        real_name=real_name,
        phone=phone,
        utm_source=utm_source
    )

    await database.save_lead_data(user_id, real_name, phone)

    await message.answer(
        "🎉 Ваша заявка успешно зарегистрирована!\n\n"
        "Мы передали контакты нашему представителю, скоро с вами свяжутся.\n"
        "Если вы хотите написать менеджеру прямо сейчас, нажмите сюда: https://t.me/narodkl_ru"
    )
"""