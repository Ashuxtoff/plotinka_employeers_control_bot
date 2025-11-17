"""Быстрый тест функции send_afternoon_reminder.

Этот скрипт вызывает функцию напрямую для проверки работы.
"""
import asyncio
import logging
from unittest.mock import AsyncMock

from bot.database import (
    init_db,
    get_users_without_answer_today,
)
from bot.scheduler import send_afternoon_reminder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def quick_test():
    """Быстрый тест функции send_afternoon_reminder."""
    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")
    
    # Получаем список пользователей, которые не ответили сегодня
    users_without_answer = await get_users_without_answer_today()
    logger.info(f"Пользователей без ответа сегодня: {len(users_without_answer)}")
    
    if not users_without_answer:
        logger.warning("Нет пользователей без ответа. Для теста нужно, чтобы кто-то не ответил сегодня.")
        logger.info("Можно временно удалить запись из work_days для тестового пользователя.")
        return
    
    for user in users_without_answer:
        logger.info(f"  - @{user.get('username', 'без username')} (tg_id={user['tg_id']})")
    
    # Создаем мок бота для проверки
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Вызываем функцию
    logger.info("Вызываю send_afternoon_reminder...")
    await send_afternoon_reminder(mock_bot)
    
    # Проверяем результат
    call_count = mock_bot.send_message.await_count
    logger.info(f"Функция вызвала send_message {call_count} раз(а)")
    
    if call_count == len(users_without_answer):
        logger.info("✅ ТЕСТ ПРОЙДЕН: Напоминания отправлены всем не ответившим пользователям")
    else:
        logger.error(f"❌ ТЕСТ НЕ ПРОЙДЕН: Ожидалось {len(users_without_answer)} вызовов, получено {call_count}")
    
    # Показываем детали вызовов
    if mock_bot.send_message.await_args_list:
        logger.info("Детали вызовов:")
        for i, call in enumerate(mock_bot.send_message.await_args_list, 1):
            args, kwargs = call
            logger.info(f"  {i}. tg_id={args[0]}, message='{args[1][:50]}...', has_keyboard={kwargs.get('reply_markup') is not None}")


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except KeyboardInterrupt:
        logger.info("Тест прерван пользователем")
