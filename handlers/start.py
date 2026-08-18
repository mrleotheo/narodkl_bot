import os
from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import database

router = Router()

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

    # Настраиваем новые кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Перейти в группу 💬", url="https://t.me/narodkl"),
            InlineKeyboardButton(text="Перейти в канал 📢", url="https://t.me/narodkl_ch")
        ],
        [
            InlineKeyboardButton(text="Оставить заявку 📝", callback_data="apply_lead")
        ],
        [
            InlineKeyboardButton(text="Написать менеджеру 👨‍💻", url="https://t.me/narodkl_ru")
        ]
    ])

    welcome_text = (
        "Привет!✌️ Наша команда - официальный представитель четырех ведущих стоматологических клиник в г. Хэйхэ (КНР). "
        "Сами мы базируемся в Благовещенске (Амурская область). От Китая нас отделяет всего 800 метров через реку Амур. 🇷🇺🤝🇨🇳\n\n"
        "❗️ Более 13 лет мы помогаем пациентам даже с самыми запущенными случаями (например, когда отсутствует 6 и более зубов) "
        "кардинально решить проблему. Около 95% наших клиентов рекомендуют нас своим близким и друзьям (остальные просто предпочитают не афишировать лечение 😉).\n\n"
        "💴 Стоматологические услуги в Китае стоят в 2–4 раза дешевле российских аналогов, а сам процесс лечения проходит в разы быстрее, "
        "что критически важно, когда восстановить зубы нужно срочно. ⏳"
    )

    photo_path = "welcome.jpg"

    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(
            text=f"[Картинка welcome.jpg не найдена]\n\n{welcome_text}",
            reply_markup=keyboard
        )