"""Конфигурация бота."""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = "Asia/Yekaterinburg"
MORNING_BROADCAST_TIME = os.getenv("MORNING_BROADCAST_TIME", "08:00")
AFTERNOON_REMINDER_TIME = os.getenv("AFTERNOON_REMINDER_TIME", "15:00")

# Список администраторов по умолчанию (username без @)
DEFAULT_ADMINS = ["mirvien", "ashuxtoff"]

# Список тестовых пользователей по умолчанию (username без @)
# Эти пользователи будут созданы как неактивные сотрудники при инициализации БД
DEFAULT_TEST_USERS = ["mfilaeff"]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
