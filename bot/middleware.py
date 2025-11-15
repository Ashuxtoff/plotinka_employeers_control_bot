"""Middleware для проверки доступа пользователей."""
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.database import is_user_registered, is_user_exists, register_admin_if_needed

logger = logging.getLogger(__name__)


class AccessControlMiddleware(BaseMiddleware):
    """Middleware для проверки доступа пользователей к боту."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка доступа перед обработкой события."""
        # Проверяем только сообщения (Message)
        if not isinstance(event, Message):
            return await handler(event, data)
        
        # Получаем данные пользователя из сообщения
        if not event.from_user:
            logger.warning("Сообщение без from_user")
            return await handler(event, data)
        
        user_id = event.from_user.id
        username = event.from_user.username
        name = event.from_user.full_name or event.from_user.first_name or "Пользователь"
        
        # Команда /start доступна всем для регистрации и согласия
        if event.text and event.text.startswith('/start'):
            # Пытаемся автоматически зарегистрировать администратора
            if username and not await is_user_registered(user_id):
                admin_registered = await register_admin_if_needed(user_id, username, name)
                # Если не админ, пытаемся обновить tg_id тестового пользователя
                if not admin_registered:
                    from bot.database import get_user_by_username, update_user_tg_id
                    test_user = await get_user_by_username(username)
                    if test_user and test_user['tg_id'] < 0:
                        success = await update_user_tg_id(test_user['tg_id'], user_id)
                        if success:
                            logger.info(f"Обновлён placeholder тестового пользователя @{username} в middleware")
            return await handler(event, data)
        
        # Кнопки согласия также должны быть доступны (для обработки ответа)
        if event.text in ["✅ Да, согласен", "❌ Нет, не согласен"]:
            # Проверяем, существует ли пользователь в БД (даже если неактивен)
            if await is_user_exists(user_id):
                return await handler(event, data)
            # Если пользователя нет - блокируем
            await event.answer("🚫 Доступ закрыт.")
            return
        
        # Проверяем, зарегистрирован ли пользователь и активен ли он
        if not await is_user_registered(user_id):
            # Пытаемся автоматически зарегистрировать администратора
            if username and await register_admin_if_needed(user_id, username, name):
                logger.info(f"Администратор @{username} автоматически зарегистрирован")
                # После регистрации продолжаем обработку
                return await handler(event, data)
            
            # Пользователь не зарегистрирован и не является администратором
            logger.info(f"Доступ закрыт для пользователя {user_id} (@{username})")
            await event.answer("🚫 Доступ закрыт.")
            return  # Прерываем обработку
        
        # Пользователь зарегистрирован, продолжаем обработку
        return await handler(event, data)

