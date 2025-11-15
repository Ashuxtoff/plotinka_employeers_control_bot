"""Тесты для модуля middleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Update

from bot.middleware import AccessControlMiddleware
from bot.database import create_user, update_user_consent, update_user_active_flag


@pytest.mark.asyncio
async def test_middleware_allows_start_command(test_db, mock_message):
    """Тест: middleware разрешает команду /start."""
    mock_message.text = "/start"
    
    handler = AsyncMock(return_value="handler_result")
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, mock_message, {})
    
    # Handler должен быть вызван
    handler.assert_called_once()
    assert result == "handler_result"


@pytest.mark.asyncio
async def test_middleware_allows_consent_buttons(test_db, mock_message):
    """Тест: middleware разрешает кнопки согласия для существующих пользователей."""
    # Создаём пользователя
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee"
    )
    
    mock_message.text = "✅ Да, согласен"
    
    handler = AsyncMock(return_value="handler_result")
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, mock_message, {})
    
    # Handler должен быть вызван
    handler.assert_called_once()
    assert result == "handler_result"


@pytest.mark.asyncio
async def test_middleware_blocks_consent_buttons_for_nonexistent_user(test_db, mock_message):
    """Тест: middleware блокирует кнопки согласия для несуществующих пользователей."""
    mock_message.text = "✅ Да, согласен"
    
    handler = AsyncMock()
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, mock_message, {})
    
    # Handler не должен быть вызван
    handler.assert_not_called()
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once_with("🚫 Доступ закрыт.")


@pytest.mark.asyncio
async def test_middleware_allows_registered_user(test_db, mock_message):
    """Тест: middleware разрешает доступ зарегистрированному активному пользователю."""
    # Создаём активного пользователя с согласием
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=True
    )
    await update_user_consent(mock_message.from_user.id, True)
    
    mock_message.text = "/some_command"
    
    handler = AsyncMock(return_value="handler_result")
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, mock_message, {})
    
    # Handler должен быть вызван
    handler.assert_called_once()
    assert result == "handler_result"


@pytest.mark.asyncio
async def test_middleware_blocks_unregistered_user(test_db, mock_message):
    """Тест: middleware блокирует доступ незарегистрированному пользователю."""
    mock_message.text = "/some_command"
    
    handler = AsyncMock()
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, mock_message, {})
    
    # Handler не должен быть вызван
    handler.assert_not_called()
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once_with("🚫 Доступ закрыт.")


@pytest.mark.asyncio
async def test_middleware_blocks_inactive_user(test_db, mock_message):
    """Тест: middleware блокирует доступ неактивному пользователю."""
    # Создаём неактивного пользователя
    await create_user(
        tg_id=mock_message.from_user.id,
        username=mock_message.from_user.username,
        name=mock_message.from_user.full_name,
        role="employee",
        active=False
    )
    
    mock_message.text = "/some_command"
    
    handler = AsyncMock()
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, mock_message, {})
    
    # Handler не должен быть вызван
    handler.assert_not_called()
    # Должно быть отправлено сообщение о блокировке
    mock_message.answer.assert_called_once_with("🚫 Доступ закрыт.")


@pytest.mark.asyncio
async def test_middleware_auto_registers_admin(test_db, mock_admin_user, mock_chat):
    """Тест: middleware автоматически регистрирует администратора."""
    from unittest.mock import AsyncMock
    from aiogram.types import Message
    
    message = AsyncMock(spec=Message)
    message.from_user = mock_admin_user
    message.chat = mock_chat
    message.text = "/some_command"
    message.answer = AsyncMock()
    
    # Мокаем register_admin_if_needed, чтобы он создал админа
    with patch('bot.middleware.register_admin_if_needed', new_callable=AsyncMock) as mock_register:
        mock_register.return_value = True
        
        handler = AsyncMock(return_value="handler_result")
        middleware = AccessControlMiddleware()
        
        result = await middleware(handler, message, {})
        
        # register_admin_if_needed должен быть вызван
        mock_register.assert_called_once()
        # Handler должен быть вызван после регистрации
        handler.assert_called_once()
        assert result == "handler_result"


@pytest.mark.asyncio
async def test_middleware_skips_non_message_events(test_db):
    """Тест: middleware пропускает события, которые не являются сообщениями."""
    # Создаём объект, который не является Message
    update = MagicMock(spec=Update)
    
    handler = AsyncMock(return_value="handler_result")
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, update, {})
    
    # Handler должен быть вызван без проверок
    handler.assert_called_once()
    assert result == "handler_result"


@pytest.mark.asyncio
async def test_middleware_handles_message_without_from_user(test_db):
    """Тест: middleware обрабатывает сообщение без from_user."""
    message = AsyncMock(spec=Message)
    message.from_user = None
    message.text = "/some_command"
    
    handler = AsyncMock(return_value="handler_result")
    middleware = AccessControlMiddleware()
    
    result = await middleware(handler, message, {})
    
    # Handler должен быть вызван (middleware просто пропускает)
    handler.assert_called_once()
    assert result == "handler_result"

