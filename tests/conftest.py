"""Общие фикстуры для тестов."""
import os
import pytest
import aiosqlite
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import User, Message, Chat
from aiogram.fsm.context import FSMContext

from bot.database import init_db, DB_PATH


@pytest.fixture
def test_db_path(tmp_path):
    """Возвращает путь к тестовой БД во временной директории."""
    test_db = tmp_path / "test_bot_data.db"
    return str(test_db)


@pytest.fixture
async def test_db(test_db_path, monkeypatch):
    """Создаёт тестовую БД и временно заменяет DB_PATH."""
    # Сохраняем оригинальный путь
    original_path = DB_PATH
    
    # Временно заменяем путь к БД
    import bot.database
    monkeypatch.setattr(bot.database, "DB_PATH", test_db_path)
    
    # Инициализируем тестовую БД
    await init_db()
    
    yield test_db_path
    
    # Восстанавливаем оригинальный путь
    monkeypatch.setattr(bot.database, "DB_PATH", original_path)
    
    # Удаляем тестовую БД
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def mock_user():
    """Создаёт мок пользователя Telegram."""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.full_name = "Test User"
    user.is_bot = False
    return user


@pytest.fixture
def mock_admin_user():
    """Создаёт мок администратора Telegram."""
    user = MagicMock(spec=User)
    user.id = 999999999
    user.username = "admin"
    user.first_name = "Admin"
    user.last_name = "User"
    user.full_name = "Admin User"
    user.is_bot = False
    return user


@pytest.fixture
def mock_chat():
    """Создаёт мок чата Telegram."""
    chat = MagicMock(spec=Chat)
    chat.id = 123456789
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Создаёт мок сообщения Telegram."""
    message = AsyncMock(spec=Message)
    message.message_id = 1
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "/start"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Создаёт мок FSMContext."""
    state = AsyncMock(spec=FSMContext)
    state.data = {}
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_bot():
    """Создаёт мок бота Telegram."""
    bot = AsyncMock()
    bot.id = 123456
    bot.username = "test_bot"
    bot.get_me = AsyncMock(return_value=MagicMock(id=123456, username="test_bot"))
    return bot


@pytest.fixture
def sample_user_data():
    """Возвращает примерные данные пользователя."""
    return {
        "tg_id": 123456789,
        "username": "testuser",
        "name": "Test User",
        "role": "employee",
        "active_flag": 1,
        "consent_given": 0,
        "created_at": "2025-01-01T00:00:00+05:00"
    }


@pytest.fixture
def sample_admin_data():
    """Возвращает примерные данные администратора."""
    return {
        "tg_id": 999999999,
        "username": "admin",
        "name": "Admin User",
        "role": "admin",
        "active_flag": 1,
        "consent_given": 1,
        "created_at": "2025-01-01T00:00:00+05:00"
    }

