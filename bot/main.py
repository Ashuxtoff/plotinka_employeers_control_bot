"""Точка входа для Telegram-бота."""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.database import (
    init_db,
    create_default_admin,
    create_default_test_users,
    fix_test_users_active_flag,
)
from bot.handlers import register, start, work_format
from bot.middleware import AccessControlMiddleware
from bot.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота."""
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создание администратора по умолчанию
    await create_default_admin()
    
    # Создание тестовых пользователей по умолчанию
    await create_default_test_users()
    
    # Исправление active_flag для тестовых пользователей (на случай, если они уже существуют)
    await fix_test_users_active_flag()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем middleware для проверки доступа
    dp.message.middleware(AccessControlMiddleware())
    
    # Регистрируем обработчики
    dp.include_router(start.router)
    dp.include_router(register.router)
    dp.include_router(work_format.router)
    
    logger.info("Бот запущен")
    
    scheduler = None
    try:
        scheduler = await start_scheduler(bot)
        await dp.start_polling(bot)
    finally:
        if scheduler:
            await shutdown_scheduler(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
