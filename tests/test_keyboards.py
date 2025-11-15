"""Тесты для модуля keyboards."""
import pytest
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.keyboards import get_consent_keyboard, get_work_format_keyboard, WORK_FORMATS


def test_get_consent_keyboard():
    """Тест: создание клавиатуры для согласия."""
    keyboard = get_consent_keyboard()
    
    # Проверяем тип
    assert isinstance(keyboard, ReplyKeyboardMarkup)
    
    # Проверяем структуру клавиатуры
    assert len(keyboard.keyboard) == 1  # Одна строка
    assert len(keyboard.keyboard[0]) == 2  # Две кнопки
    
    # Проверяем текст кнопок
    button1 = keyboard.keyboard[0][0]
    button2 = keyboard.keyboard[0][1]
    
    assert isinstance(button1, KeyboardButton)
    assert isinstance(button2, KeyboardButton)
    
    assert button1.text == "✅ Да, согласен"
    assert button2.text == "❌ Нет, не согласен"
    
    # Проверяем свойства клавиатуры
    assert keyboard.resize_keyboard is True
    assert keyboard.one_time_keyboard is True


def test_get_consent_keyboard_buttons_order():
    """Тест: порядок кнопок в клавиатуре согласия."""
    keyboard = get_consent_keyboard()
    
    # Первая кнопка - согласие
    assert keyboard.keyboard[0][0].text == "✅ Да, согласен"
    # Вторая кнопка - отказ
    assert keyboard.keyboard[0][1].text == "❌ Нет, не согласен"


def test_get_consent_keyboard_immutability():
    """Тест: клавиатура создаётся заново при каждом вызове."""
    keyboard1 = get_consent_keyboard()
    keyboard2 = get_consent_keyboard()
    
    # Это должны быть разные объекты
    assert keyboard1 is not keyboard2
    
    # Но с одинаковой структурой
    assert keyboard1.keyboard[0][0].text == keyboard2.keyboard[0][0].text
    assert keyboard1.keyboard[0][1].text == keyboard2.keyboard[0][1].text


def test_work_formats_list():
    """Тест: список форматов работы содержит все необходимые форматы."""
    expected_formats = [
        "Офис",
        "Удалёнка",
        "Учёба",
        "Болезнь",
        "Отпуск",
        "Отгул неоплачиваемый",
        "Отгул оплачиваемый",
        "Экспедиция"
    ]
    
    assert len(WORK_FORMATS) == len(expected_formats)
    for format_text in expected_formats:
        assert format_text in WORK_FORMATS


def test_get_work_format_keyboard():
    """Тест: создание клавиатуры для выбора формата работы."""
    keyboard = get_work_format_keyboard()
    
    # Проверяем тип
    assert isinstance(keyboard, ReplyKeyboardMarkup)
    
    # Проверяем структуру клавиатуры (4 строки)
    assert len(keyboard.keyboard) == 4
    
    # Проверяем количество кнопок в каждой строке
    assert len(keyboard.keyboard[0]) == 2  # Офис, Удалёнка
    assert len(keyboard.keyboard[1]) == 2  # Учёба, Болезнь
    assert len(keyboard.keyboard[2]) == 2  # Отпуск, Экспедиция
    assert len(keyboard.keyboard[3]) == 2  # Отгул неоплачиваемый, Отгул оплачиваемый
    
    # Проверяем текст кнопок
    assert keyboard.keyboard[0][0].text == "Офис"
    assert keyboard.keyboard[0][1].text == "Удалёнка"
    assert keyboard.keyboard[1][0].text == "Учёба"
    assert keyboard.keyboard[1][1].text == "Болезнь"
    assert keyboard.keyboard[2][0].text == "Отпуск"
    assert keyboard.keyboard[2][1].text == "Экспедиция"
    assert keyboard.keyboard[3][0].text == "Отгул неоплачиваемый"
    assert keyboard.keyboard[3][1].text == "Отгул оплачиваемый"
    
    # Проверяем свойства клавиатуры
    assert keyboard.resize_keyboard is True
    assert keyboard.one_time_keyboard is True


def test_get_work_format_keyboard_all_formats_present():
    """Тест: все форматы из WORK_FORMATS присутствуют в клавиатуре."""
    keyboard = get_work_format_keyboard()
    
    # Собираем все тексты кнопок
    button_texts = []
    for row in keyboard.keyboard:
        for button in row:
            button_texts.append(button.text)
    
    # Проверяем, что все форматы присутствуют
    for format_text in WORK_FORMATS:
        assert format_text in button_texts


def test_get_work_format_keyboard_immutability():
    """Тест: клавиатура создаётся заново при каждом вызове."""
    keyboard1 = get_work_format_keyboard()
    keyboard2 = get_work_format_keyboard()
    
    # Это должны быть разные объекты
    assert keyboard1 is not keyboard2
    
    # Но с одинаковой структурой
    assert len(keyboard1.keyboard) == len(keyboard2.keyboard)
    for i in range(len(keyboard1.keyboard)):
        assert len(keyboard1.keyboard[i]) == len(keyboard2.keyboard[i])
        for j in range(len(keyboard1.keyboard[i])):
            assert keyboard1.keyboard[i][j].text == keyboard2.keyboard[i][j].text

