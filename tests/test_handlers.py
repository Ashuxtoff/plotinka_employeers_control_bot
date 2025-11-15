"""Тесты для обработчиков команд."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message

from bot.handlers import start, work_format
from bot.database import (
    create_user,
    update_user_consent,
    update_user_active_flag,
    get_user_by_tg_id,
    is_user_registered,
    add_work_day,
    get_work_day
)
from bot.keyboards import WORK_FORMATS
from bot.utils.date_utils import get_today_date


@pytest.mark.asyncio
async def test_cmd_start_new_user_without_consent(test_db, mock_message):
    """Тест: команда /start для нового пользователя без согласия."""
    # Создаём пользователя без согласия
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    
    mock_message.text = "/start"
    
    await start.cmd_start(mock_message)
    
    # Должно быть отправлено сообщение с запросом согласия
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "согласие" in call_args[0][0].lower() or "согласен" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_user_with_consent(test_db, mock_message):
    """Тест: команда /start для пользователя с согласием."""
    # Создаём активного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    mock_message.text = "/start"
    
    await start.cmd_start(mock_message)
    
    # Должно быть отправлено приветственное сообщение
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "добро пожаловать" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_inactive_user(test_db, mock_message):
    """Тест: команда /start для неактивного пользователя."""
    # Создаём неактивного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=False
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    mock_message.text = "/start"
    
    await start.cmd_start(mock_message)
    
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "доступ закрыт" in call_args[0][0].lower() or "деактивирован" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_unregistered_user(test_db, mock_message):
    """Тест: команда /start для незарегистрированного пользователя."""
    mock_message.text = "/start"
    
    await start.cmd_start(mock_message)
    
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "доступ закрыт" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_auto_register_admin(test_db, mock_admin_user, mock_chat):
    """Тест: команда /start автоматически регистрирует администратора."""
    from aiogram.types import Message
    
    message = AsyncMock(spec=Message)
    message.from_user = mock_admin_user
    message.chat = mock_chat
    message.text = "/start"
    message.answer = AsyncMock()
    
    # Мокаем register_admin_if_needed
    with patch('bot.handlers.start.register_admin_if_needed', new_callable=AsyncMock) as mock_register:
        mock_register.return_value = True
        
        await start.cmd_start(message)
        
        # register_admin_if_needed должен быть вызван
        mock_register.assert_called_once()
        # Должно быть отправлено сообщение
        message.answer.assert_called()


@pytest.mark.asyncio
async def test_handle_consent_yes(test_db, mock_message):
    """Тест: обработка согласия - пользователь согласен."""
    # Создаём пользователя
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    
    mock_message.text = "✅ Да, согласен"
    
    await start.handle_consent(mock_message)
    
    # Проверяем, что согласие сохранено
    user = await get_user_by_tg_id(mock_message.from_user.id)
    assert user["consent_given"] == 1
    
    # Должно быть отправлено подтверждение
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "спасибо" in call_args[0][0].lower() or "согласие" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_consent_yes_inactive_user(test_db, mock_message):
    """Тест: обработка согласия - пользователь согласен, но неактивен."""
    # Создаём неактивного пользователя
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=False
    )
    
    mock_message.text = "✅ Да, согласен"
    
    await start.handle_consent(mock_message)
    
    # Проверяем, что согласие сохранено
    user = await get_user_by_tg_id(mock_message.from_user.id)
    assert user["consent_given"] == 1
    
    # Должно быть отправлено сообщение о деактивации
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "деактивирован" in call_args[0][0].lower() or "администратор" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_consent_no(test_db, mock_message):
    """Тест: обработка согласия - пользователь не согласен."""
    # Создаём пользователя
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    
    mock_message.text = "❌ Нет, не согласен"
    
    await start.handle_consent(mock_message)
    
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "доступ закрыт" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_consent_unregistered_user(test_db, mock_message):
    """Тест: обработка согласия - незарегистрированный пользователь."""
    mock_message.text = "✅ Да, согласен"
    
    await start.handle_consent(mock_message)
    
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "доступ закрыт" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_updates_test_user_placeholder(test_db, mock_message):
    """Тест: команда /start обновляет placeholder тестового пользователя."""
    from bot.config import DEFAULT_TEST_USERS
    
    if not DEFAULT_TEST_USERS:
        pytest.skip("Нет тестовых пользователей в конфиге")
    
    test_username = DEFAULT_TEST_USERS[0]
    mock_message.from_user.username = test_username
    
    # Создаём placeholder с отрицательным ID
    await create_user(
        tg_id=-100,
        username=test_username,
        name="Test User",
        role="employee",
        active=True
    )
    
    mock_message.text = "/start"
    
    with patch('bot.handlers.start.get_user_by_username', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"tg_id": -100, "active_flag": 1}
        
        with patch('bot.handlers.start.update_user_tg_id', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True
            
            await start.cmd_start(mock_message)
            
            # update_user_tg_id должен быть вызван
            mock_update.assert_called()


# Тесты для обработчика выбора формата работы
@pytest.mark.asyncio
async def test_handle_work_format_success(test_db, mock_message):
    """Тест: успешный выбор формата работы."""
    # Создаём активного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    mock_message.text = "Офис"
    
    await work_format.handle_work_format(mock_message)
    
    # Проверяем, что формат сохранён в БД
    today = get_today_date()
    work_day = await get_work_day(mock_message.from_user.id, today)
    assert work_day is not None
    assert work_day["status"] == "Офис"
    
    # Должно быть отправлено подтверждение
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "формат работы сохранён" in call_args[0][0].lower() or "сохранён" in call_args[0][0].lower()
    assert "офис" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_work_format_all_formats(test_db, mock_message):
    """Тест: выбор всех форматов работы."""
    # Создаём активного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    today = get_today_date()
    
    # Проверяем все форматы
    for format_text in WORK_FORMATS:
        mock_message.text = format_text
        mock_message.answer.reset_mock()
        
        await work_format.handle_work_format(mock_message)
        
        # Проверяем, что формат сохранён
        work_day = await get_work_day(mock_message.from_user.id, today)
        assert work_day is not None
        assert work_day["status"] == format_text
        
        # Должно быть отправлено подтверждение
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert format_text.lower() in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_work_format_unregistered_user(test_db, mock_message):
    """Тест: выбор формата незарегистрированным пользователем."""
    mock_message.text = "Офис"
    
    await work_format.handle_work_format(mock_message)
    
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "доступ закрыт" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_work_format_no_consent(test_db, mock_message):
    """Тест: выбор формата пользователем без согласия."""
    # Создаём пользователя без согласия
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    
    mock_message.text = "Офис"
    
    await work_format.handle_work_format(mock_message)
    
    # Должно быть отправлено сообщение о необходимости согласия
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "согласие" in call_args[0][0].lower() or "согласен" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_work_format_inactive_user(test_db, mock_message):
    """Тест: выбор формата неактивным пользователем."""
    # Создаём неактивного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=False
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    mock_message.text = "Офис"
    
    await work_format.handle_work_format(mock_message)
    
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "доступ закрыт" in call_args[0][0].lower() or "деактивирован" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_work_format_update_existing(test_db, mock_message):
    """Тест: обновление существующей записи о формате работы."""
    # Создаём активного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    today = get_today_date()
    
    # Сначала выбираем один формат
    mock_message.text = "Офис"
    await work_format.handle_work_format(mock_message)
    
    # Проверяем, что сохранён "Офис"
    work_day = await get_work_day(mock_message.from_user.id, today)
    assert work_day["status"] == "Офис"
    
    # Затем меняем на другой формат
    mock_message.text = "Удалёнка"
    mock_message.answer.reset_mock()
    await work_format.handle_work_format(mock_message)
    
    # Проверяем, что обновился на "Удалёнка"
    work_day = await get_work_day(mock_message.from_user.id, today)
    assert work_day["status"] == "Удалёнка"
    
    # Должно быть отправлено подтверждение
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "удалёнка" in call_args[0][0].lower()

