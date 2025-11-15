"""Тесты для модуля date_utils."""
import pytest
from datetime import datetime
import pytz

from bot.utils.date_utils import (
    get_today_date,
    format_date_for_display,
    validate_date,
    parse_date_range,
    generate_date_range
)
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


# Тесты для validate_date
def test_validate_date_full_format():
    """Тест: валидация даты в формате dd.MM.YYYY."""
    success, msg, date_obj = validate_date("15.11.2025")
    
    assert success is True
    assert msg == ""
    assert date_obj is not None
    assert date_obj.year == 2025
    assert date_obj.month == 11
    assert date_obj.day == 15


def test_validate_date_short_format():
    """Тест: валидация даты в формате dd.MM (без года)."""
    # Получаем текущий год
    current_year = datetime.now(pytz.timezone(TIMEZONE)).year
    
    success, msg, date_obj = validate_date("15.11")
    
    assert success is True
    assert msg == ""
    assert date_obj is not None
    assert date_obj.year == current_year  # Должен использоваться текущий год
    assert date_obj.month == 11
    assert date_obj.day == 15


def test_validate_date_empty():
    """Тест: валидация пустой даты."""
    success, msg, date_obj = validate_date("")
    
    assert success is False
    assert "пустой" in msg.lower()
    assert date_obj is None


def test_validate_date_none():
    """Тест: валидация None (строки из пробелов)."""
    success, msg, date_obj = validate_date("   ")
    
    assert success is False
    assert "пустой" in msg.lower()
    assert date_obj is None


def test_validate_date_invalid_format():
    """Тест: валидация даты в неверном формате."""
    test_cases = [
        "2025-11-15",  # Неправильный формат
        "15/11/2025",  # Неправильный разделитель
        "15.11.25",    # Неполный год
        "15.11.",      # Точка в конце
        ".11.2025",    # Пустой день
        "abc.def.ghij", # Не числа
        "1.1",         # Слишком короткие числа (хотя это должно пройти)
    ]
    
    for date_str in test_cases:
        success, msg, date_obj = validate_date(date_str)
        # Некоторые могут пройти валидацию формата, но упасть на парсинге
        if date_str in ["1.1"]:  # Это может пройти
            continue
        assert success is False, f"Дата {date_str} должна быть невалидной"
        assert "формат" in msg.lower() or "ошибка" in msg.lower()
        assert date_obj is None


def test_validate_date_invalid_date():
    """Тест: валидация некорректной даты."""
    test_cases = [
        ("32.01.2025", "день больше 31"),
        ("31.04.2025", "в апреле только 30 дней"),
        ("29.02.2025", "29 февраля в невисокосном году"),
        ("00.01.2025", "нулевой день"),
        ("15.13.2025", "месяц больше 12"),
        ("15.00.2025", "нулевой месяц"),
    ]
    
    for date_str, description in test_cases:
        success, msg, date_obj = validate_date(date_str)
        assert success is False, f"Дата {date_str} ({description}) должна быть невалидной"
        assert "некорректная" in msg.lower() or "ошибка" in msg.lower()
        assert date_obj is None


def test_validate_date_valid_leap_year():
    """Тест: валидация 29 февраля в високосном году."""
    success, msg, date_obj = validate_date("29.02.2024")
    
    assert success is True
    assert msg == ""
    assert date_obj is not None
    assert date_obj.year == 2024
    assert date_obj.month == 2
    assert date_obj.day == 29


def test_validate_date_single_digit():
    """Тест: валидация даты с однозначными числами."""
    success, msg, date_obj = validate_date("5.3.2025")
    
    assert success is True
    assert msg == ""
    assert date_obj is not None
    assert date_obj.year == 2025
    assert date_obj.month == 3
    assert date_obj.day == 5


# Тесты для parse_date_range
def test_parse_date_range_full_format():
    """Тест: разбор диапазона дат в полном формате."""
    success, msg, start_date, end_date = parse_date_range("15.11.2025 - 20.11.2025")
    
    assert success is True
    assert msg == ""
    assert start_date is not None
    assert end_date is not None
    assert start_date.date() == datetime(2025, 11, 15).date()
    assert end_date.date() == datetime(2025, 11, 20).date()


def test_parse_date_range_short_format():
    """Тест: разбор диапазона дат в коротком формате."""
    # Получаем текущий год
    current_year = datetime.now(pytz.timezone(TIMEZONE)).year
    
    success, msg, start_date, end_date = parse_date_range("15.11 - 20.11")
    
    assert success is True
    assert msg == ""
    assert start_date is not None
    assert end_date is not None
    assert start_date.date() == datetime(current_year, 11, 15).date()
    assert end_date.date() == datetime(current_year, 11, 20).date()


def test_parse_date_range_with_spaces():
    """Тест: разбор диапазона дат с пробелами вокруг дефиса."""
    success, msg, start_date, end_date = parse_date_range("15.11.2025  -  20.11.2025")
    
    assert success is True
    assert msg == ""
    assert start_date is not None
    assert end_date is not None


def test_parse_date_range_single_date():
    """Тест: разбор диапазона с одной датой (одна и та же дата)."""
    success, msg, start_date, end_date = parse_date_range("15.11.2025 - 15.11.2025")
    
    assert success is True
    assert msg == ""
    assert start_date is not None
    assert end_date is not None
    assert start_date.date() == end_date.date()


def test_parse_date_range_empty():
    """Тест: разбор пустого диапазона."""
    success, msg, start_date, end_date = parse_date_range("")
    
    assert success is False
    assert "пуст" in msg.lower()
    assert start_date is None
    assert end_date is None


def test_parse_date_range_invalid_format():
    """Тест: разбор диапазона в неверном формате."""
    test_cases = [
        "15.11.2025",  # Только одна дата
        "15.11.2025 -",  # Отсутствует конечная дата
        "- 20.11.2025",  # Отсутствует начальная дата
        "15.11.2025 20.11.2025",  # Нет дефиса
    ]
    
    for date_range in test_cases:
        success, msg, start_date, end_date = parse_date_range(date_range)
        assert success is False, f"Диапазон {date_range} должен быть невалидным"
        assert start_date is None or end_date is None


def test_parse_date_range_start_after_end():
    """Тест: разбор диапазона, где начальная дата позже конечной."""
    success, msg, start_date, end_date = parse_date_range("20.11.2025 - 15.11.2025")
    
    assert success is False
    assert "позже" in msg.lower() or "раньше" in msg.lower()
    assert start_date is not None  # Даты валидны, но порядок неправильный
    assert end_date is not None


def test_parse_date_range_invalid_start_date():
    """Тест: разбор диапазона с невалидной начальной датой."""
    success, msg, start_date, end_date = parse_date_range("32.11.2025 - 20.11.2025")
    
    assert success is False
    assert "начальной" in msg.lower()
    assert start_date is None


def test_parse_date_range_invalid_end_date():
    """Тест: разбор диапазона с невалидной конечной датой."""
    success, msg, start_date, end_date = parse_date_range("15.11.2025 - 32.11.2025")
    
    assert success is False
    assert "конечной" in msg.lower()
    assert end_date is None


def test_parse_date_range_mixed_formats():
    """Тест: разбор диапазона с разными форматами (полный и короткий)."""
    current_year = datetime.now(pytz.timezone(TIMEZONE)).year
    
    success, msg, start_date, end_date = parse_date_range("15.11.2025 - 20.11")
    
    assert success is True
    assert start_date.date() == datetime(2025, 11, 15).date()
    assert end_date.date() == datetime(current_year, 11, 20).date()


# Тесты для generate_date_range
def test_generate_date_range_single_day():
    """Тест: генерация диапазона для одного дня."""
    tz_mock = pytz.timezone(TIMEZONE)
    start = tz_mock.localize(datetime(2025, 11, 15))
    end = tz_mock.localize(datetime(2025, 11, 15))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 1
    assert date_list[0] == "2025-11-15"


def test_generate_date_range_multiple_days():
    """Тест: генерация диапазона для нескольких дней."""
    tz_mock = pytz.timezone(TIMEZONE)
    start = tz_mock.localize(datetime(2025, 11, 15))
    end = tz_mock.localize(datetime(2025, 11, 20))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 6
    assert date_list[0] == "2025-11-15"
    assert date_list[5] == "2025-11-20"
    assert date_list == [
        "2025-11-15",
        "2025-11-16",
        "2025-11-17",
        "2025-11-18",
        "2025-11-19",
        "2025-11-20"
    ]


def test_generate_date_range_month_boundary():
    """Тест: генерация диапазона с переходом через границу месяца."""
    tz_mock = pytz.timezone(TIMEZONE)
    start = tz_mock.localize(datetime(2025, 11, 30))
    end = tz_mock.localize(datetime(2025, 12, 2))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 3
    assert date_list[0] == "2025-11-30"
    assert date_list[1] == "2025-12-01"
    assert date_list[2] == "2025-12-02"


def test_generate_date_range_year_boundary():
    """Тест: генерация диапазона с переходом через границу года."""
    tz_mock = pytz.timezone(TIMEZONE)
    start = tz_mock.localize(datetime(2025, 12, 31))
    end = tz_mock.localize(datetime(2026, 1, 2))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 3
    assert date_list[0] == "2025-12-31"
    assert date_list[1] == "2026-01-01"
    assert date_list[2] == "2026-01-02"


def test_generate_date_range_start_after_end():
    """Тест: генерация диапазона, где начальная дата позже конечной."""
    tz_mock = pytz.timezone(TIMEZONE)
    start = tz_mock.localize(datetime(2025, 11, 20))
    end = tz_mock.localize(datetime(2025, 11, 15))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 0


def test_generate_date_range_none():
    """Тест: генерация диапазона с None."""
    tz_mock = pytz.timezone(TIMEZONE)
    now_with_tz = tz_mock.localize(datetime.now())
    
    date_list1 = generate_date_range(None, now_with_tz)
    assert len(date_list1) == 0
    
    date_list2 = generate_date_range(now_with_tz, None)
    assert len(date_list2) == 0
    
    date_list3 = generate_date_range(None, None)
    assert len(date_list3) == 0


def test_generate_date_range_february():
    """Тест: генерация диапазона в феврале (разные длины месяца)."""
    tz_mock = pytz.timezone(TIMEZONE)
    
    # Февраль 2025 (невисокосный год)
    start = tz_mock.localize(datetime(2025, 2, 27))
    end = tz_mock.localize(datetime(2025, 3, 1))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 3
    assert date_list[0] == "2025-02-27"
    assert date_list[1] == "2025-02-28"
    assert date_list[2] == "2025-03-01"
    
    # Февраль 2024 (високосный год)
    start = tz_mock.localize(datetime(2024, 2, 28))
    end = tz_mock.localize(datetime(2024, 3, 1))
    
    date_list = generate_date_range(start, end)
    
    assert len(date_list) == 3
    assert date_list[0] == "2024-02-28"
    assert date_list[1] == "2024-02-29"
    assert date_list[2] == "2024-03-01"

