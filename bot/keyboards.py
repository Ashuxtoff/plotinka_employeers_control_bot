"""Клавиатуры и кнопки для бота."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Список форматов работы
WORK_FORMATS = [
    "Офис",
    "Удалёнка",
    "Учёба",
    "Болезнь",
    "Отпуск",
    "Отгул неоплачиваемый",
    "Отгул оплачиваемый",
    "Экспедиция"
]


def get_consent_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру для согласия на обработку данных."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Да, согласен"),
                KeyboardButton(text="❌ Нет, не согласен")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_work_format_keyboard() -> ReplyKeyboardMarkup:
    """Создать клавиатуру для выбора формата работы."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Офис"),
                KeyboardButton(text="Удалёнка")
            ],
            [
                KeyboardButton(text="Учёба"),
                KeyboardButton(text="Болезнь")
            ],
            [
                KeyboardButton(text="Отпуск"),
                KeyboardButton(text="Экспедиция")
            ],
            [
                KeyboardButton(text="Отгул неоплачиваемый"),
                KeyboardButton(text="Отгул оплачиваемый")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

