"""Утилиты для работы с датами."""
from datetime import datetime
import pytz

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

