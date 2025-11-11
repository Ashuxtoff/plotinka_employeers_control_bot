"""Конфигурация бота."""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = "Asia/Yekaterinburg"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
