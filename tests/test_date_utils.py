"""Тесты для модуля date_utils."""
import pytest
from datetime import datetime
from unittest.mock import patch
import pytz

from bot.utils.date_utils import get_today_date, format_date_for_display
from bot.config import TIMEZONE


def test_get_today_date_format():
    """Тест: формат возвращаемой даты."""
    date_str = get_today_date()
    
    # Проверяем формат YYYY-MM-DD
    assert len(date_str) == 10
    assert date_str.count("-") == 2
    
    # Проверяем, что можно распарсить дату
    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
    assert isinstance(parsed_date, datetime)


def test_get_today_date_timezone():
    """Тест: дата учитывает часовой пояс."""
    tz = pytz.timezone(TIMEZONE)
    
    # Получаем дату через утилиту
    date_str = get_today_date()
    
    # Получаем текущую дату в нужном часовом поясе
    now_tz = datetime.now(tz)
    expected_date = now_tz.strftime("%Y-%m-%d")
    
    # Даты должны совпадать
    assert date_str == expected_date


def test_format_date_for_display_valid():
    """Тест: форматирование валидной даты."""
    date_str = "2025-11-15"
    formatted = format_date_for_display(date_str)
    
    assert formatted == "15.11.2025"


def test_format_date_for_display_different_dates():
    """Тест: форматирование разных дат."""
    test_cases = [
        ("2025-01-01", "01.01.2025"),
        ("2025-12-31", "31.12.2025"),
        ("2025-02-28", "28.02.2025"),  # Обычный год
        ("2024-02-29", "29.02.2024"),  # Високосный год
    ]
    
    for input_date, expected_output in test_cases:
        result = format_date_for_display(input_date)
        assert result == expected_output, f"Ожидалось {expected_output}, получено {result} для {input_date}"


def test_format_date_for_display_invalid():
    """Тест: форматирование невалидной даты возвращает исходную строку."""
    invalid_date = "invalid-date"
    formatted = format_date_for_display(invalid_date)
    
    # При ошибке должна вернуться исходная строка
    assert formatted == invalid_date


def test_format_date_for_display_wrong_format():
    """Тест: форматирование даты в неправильном формате."""
    wrong_format = "15.11.2025"  # Уже в формате для отображения
    formatted = format_date_for_display(wrong_format)
    
    # Должна вернуться исходная строка, так как формат не YYYY-MM-DD
    assert formatted == wrong_format


def test_get_today_date_consistency():
    """Тест: последовательные вызовы возвращают одинаковую дату (если вызваны в один день)."""
    date1 = get_today_date()
    date2 = get_today_date()
    
    # В один день должны быть одинаковыми
    assert date1 == date2

