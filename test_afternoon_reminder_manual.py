"""Скрипт для ручного тестирования дневных напоминаний.

Этот скрипт:
1. Устанавливает время напоминания на ближайшие минуты (через 2 минуты)
2. Показывает список пользователей, которые не ответили сегодня
3. Запускает бота для проверки работы напоминаний
"""
import asyncio
import logging
from datetime import datetime, timedelta
import pytz

from bot.config import BOT_TOKEN, TIMEZONE
from bot.database import (
    init_db,
    set_setting,
    get_afternoon_reminder_time,
    get_users_without_answer_today,
    SETTING_AFTERNOON_TIME,
)
from bot.scheduler import send_afternoon_reminder, start_scheduler, shutdown_scheduler
from aiogram import Bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

tz = pytz.timezone(TIMEZONE)


async def test_afternoon_reminder():
    """Тестирование дневных напоминаний."""
    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")
    
    # Получаем текущее время
    now = datetime.now(tz)
    logger.info(f"Текущее время: {now.strftime('%H:%M:%S')}")
    
    # Устанавливаем время напоминания на 2 минуты вперед
    test_time = (now + timedelta(minutes=2)).strftime("%H:%M")
    logger.info(f"Устанавливаю время напоминания на {test_time}")
    await set_setting(SETTING_AFTERNOON_TIME, test_time)
    
    # Проверяем, что время установлено
    current_time = await get_afternoon_reminder_time()
    logger.info(f"Текущее время напоминания в БД: {current_time}")
    
    # Получаем список пользователей, которые не ответили сегодня
    users_without_answer = await get_users_without_answer_today()
    logger.info(f"Пользователей без ответа сегодня: {len(users_without_answer)}")
    for user in users_without_answer:
        logger.info(f"  - @{user.get('username', 'без username')} (tg_id={user['tg_id']})")
    
    if not users_without_answer:
        logger.warning("Нет пользователей без ответа. Для теста нужно, чтобы кто-то не ответил сегодня.")
        logger.info("Можно временно удалить запись из work_days для тестового пользователя.")
        return
    
    # Создаем бота
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Запускаем планировщик
        logger.info("Запускаю планировщик...")
        scheduler = await start_scheduler(bot)
        
        logger.info("=" * 60)
        logger.info("Ожидаю срабатывания напоминания...")
        logger.info(f"Напоминание должно сработать в {test_time}")
        logger.info("=" * 60)
        
        # Ждем 3 минуты (чтобы напоминание точно сработало)
        await asyncio.sleep(180)
        
        # Также можно вызвать функцию напрямую для немедленной проверки
        logger.info("Вызываю функцию send_afternoon_reminder напрямую для проверки...")
        await send_afternoon_reminder(bot)
        
        logger.info("Тест завершен. Проверьте, что напоминания были отправлены.")
        
    finally:
        # Останавливаем планировщик
        await shutdown_scheduler(wait=False)
        await bot.session.close()
        
        # Восстанавливаем время напоминания на 15:00
        logger.info("Восстанавливаю время напоминания на 15:00")
        await set_setting(SETTING_AFTERNOON_TIME, "15:00")


if __name__ == "__main__":
    try:
        asyncio.run(test_afternoon_reminder())
    except KeyboardInterrupt:
        logger.info("Тест прерван пользователем")
