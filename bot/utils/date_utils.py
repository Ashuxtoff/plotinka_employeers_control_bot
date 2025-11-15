"""Утилиты для работы с датами."""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import pytz
import re

from bot.config import TIMEZONE

# Часовой пояс
tz = pytz.timezone(TIMEZONE)


def get_today_date() -> str:
    """
    Получить текущую дату в формате YYYY-MM-DD с учетом часового пояса.
    
    Returns:
        Строка с датой в формате YYYY-MM-DD
    """
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d")


def format_date_for_display(date_str: str) -> str:
    """
    Форматировать дату из формата YYYY-MM-DD в формат dd.MM.YYYY для отображения.
    
    Args:
        date_str: Дата в формате YYYY-MM-DD
    
    Returns:
        Строка с датой в формате dd.MM.YYYY
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d.%m.%Y")
    except ValueError:
        return date_str


def validate_date(date_str: str) -> Tuple[bool, str, Optional[datetime]]:
    """
    Валидировать дату в формате dd.MM.YYYY или dd.MM.
    
    Если год не указан, используется текущий год.
    
    Args:
        date_str: Дата в формате dd.MM.YYYY или dd.MM
    
    Returns:
        Кортеж (успех, сообщение об ошибке, объект datetime или None)
    """
    if not date_str or not date_str.strip():
        return False, "Дата не может быть пустой.", None
    
    date_str = date_str.strip()
    
    # Проверяем формат dd.MM.YYYY или dd.MM
    pattern_full = r'^\d{1,2}\.\d{1,2}\.\d{4}$'
    pattern_short = r'^\d{1,2}\.\d{1,2}$'
    
    if not (re.match(pattern_full, date_str) or re.match(pattern_short, date_str)):
        return False, "Неверный формат даты. Используйте формат дд.ММ.ГГГГ или дд.ММ", None
    
    try:
        # Разбираем дату
        parts = date_str.split('.')
        day = int(parts[0])
        month = int(parts[1])
        
        # Если год не указан, используем текущий
        if len(parts) == 2:
            year = datetime.now(tz).year
        else:
            year = int(parts[2])
        
        # Проверяем корректность даты
        date_obj = datetime(year, month, day)
        
        return True, "", date_obj.replace(tzinfo=tz)
        
    except ValueError as e:
        error_msg = str(e)
        if "day is out of range" in error_msg or "month must be in 1..12" in error_msg:
            return False, f"Некорректная дата: {date_str}. Проверьте день и месяц.", None
        return False, f"Ошибка при разборе даты: {error_msg}", None
    except Exception as e:
        return False, f"Неожиданная ошибка при валидации даты: {str(e)}", None


def parse_date_range(date_range_str: str) -> Tuple[bool, str, Optional[datetime], Optional[datetime]]:
    """
    Разобрать диапазон дат в формате "dd.MM.YYYY - dd.MM.YYYY" или "dd.MM - dd.MM".
    
    Валидирует обе даты и проверяет, что начальная дата <= конечной.
    
    Args:
        date_range_str: Диапазон дат в формате "dd.MM.YYYY - dd.MM.YYYY" или "dd.MM - dd.MM"
    
    Returns:
        Кортеж (успех, сообщение об ошибке, start_date или None, end_date или None)
    """
    if not date_range_str or not date_range_str.strip():
        return False, "Диапазон дат не может быть пустым.", None, None
    
    date_range_str = date_range_str.strip()
    
    # Разделяем по дефису (может быть пробелы вокруг)
    parts = re.split(r'\s*-\s*', date_range_str)
    
    if len(parts) != 2:
        return False, "Неверный формат диапазона дат. Используйте формат: дд.ММ.ГГГГ - дд.ММ.ГГГГ", None, None
    
    start_str = parts[0].strip()
    end_str = parts[1].strip()
    
    # Валидируем начальную дату
    start_valid, start_msg, start_date = validate_date(start_str)
    if not start_valid:
        return False, f"Ошибка в начальной дате: {start_msg}", None, None
    
    # Валидируем конечную дату
    end_valid, end_msg, end_date = validate_date(end_str)
    if not end_valid:
        return False, f"Ошибка в конечной дате: {end_msg}", None, None
    
    # Проверяем, что начальная дата <= конечной
    if start_date and end_date:
        # Сравниваем только даты, без времени
        start_date_only = start_date.date()
        end_date_only = end_date.date()
        
        if start_date_only > end_date_only:
            return False, "Начальная дата не может быть позже конечной даты.", start_date, end_date
    
    return True, "", start_date, end_date


def generate_date_range(start_date: datetime, end_date: datetime) -> List[str]:
    """
    Сгенерировать список дат в формате YYYY-MM-DD для диапазона включительно.
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
    
    Returns:
        Список строк с датами в формате YYYY-MM-DD
    """
    if not start_date or not end_date:
        return []
    
    # Получаем только даты без времени
    start = start_date.date()
    end = end_date.date()
    
    if start > end:
        return []
    
    date_list = []
    current = start
    
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        # Переходим к следующему дню
        current += timedelta(days=1)
    
    return date_list

