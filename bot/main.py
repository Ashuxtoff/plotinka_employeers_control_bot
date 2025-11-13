"""Точка входа для Telegram-бота."""
import asyncio
import logging
from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.handlers import start
from bot.database import init_db, create_default_admin

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
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем обработчики
    dp.include_router(start.router)
    
    logger.info("Бот запущен")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
