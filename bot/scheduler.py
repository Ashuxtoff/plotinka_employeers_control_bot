"""Планировщик рассылок."""
import asyncio
import logging

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import TIMEZONE
from bot.database import (
    get_active_and_consented_users,
    get_morning_broadcast_time,
    get_afternoon_reminder_time,
    get_users_without_answer_today,
)
from bot.keyboards import get_work_format_keyboard


logger = logging.getLogger(__name__)
tz = pytz.timezone(TIMEZONE)
_scheduler: AsyncIOScheduler | None = None


def _parse_time_to_cron(time_str: str) -> CronTrigger:
    """Преобразовать строку HH:MM в CronTrigger."""
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Некорректный формат времени: {time_str}")
    hour, minute = parts
    return CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)


async def send_morning_prompt(bot: Bot) -> None:
    """Отправить утреннее напоминание всем активным сотрудникам."""
    users = await get_active_and_consented_users()
    if not users:
        logger.info("Нет пользователей для утренней рассылки")
        return

    logger.info("Начинаю утреннюю рассылку для %d пользователей", len(users))
    keyboard = get_work_format_keyboard()
    for user in users:
        tg_id = user["tg_id"]
        username = user.get("username", "без username")
        try:
            await bot.send_message(
                tg_id,
                "Доброе утро! Пожалуйста, отметьте формат работы на сегодня.",
                reply_markup=keyboard,
            )
            logger.info("Утреннее сообщение отправлено пользователю @%s (tg_id=%s)", username, tg_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Не удалось отправить утреннее сообщение @%s (tg_id=%s): %s", username, tg_id, exc)


async def send_afternoon_reminder(bot: Bot) -> None:
    """Отправить дневное напоминание сотрудникам, которые не ответили до 15:00."""
    users = await get_users_without_answer_today()
    if not users:
        logger.info("Нет пользователей для дневного напоминания (все ответили)")
        return

    logger.info("Начинаю дневное напоминание для %d пользователей", len(users))
    keyboard = get_work_format_keyboard()
    for user in users:
        tg_id = user["tg_id"]
        username = user.get("username", "без username")
        try:
            await bot.send_message(
                tg_id,
                "Напоминание: пожалуйста, отметьте формат работы на сегодня.",
                reply_markup=keyboard,
            )
            logger.info("Дневное напоминание отправлено пользователю @%s (tg_id=%s)", username, tg_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Не удалось отправить дневное напоминание @%s (tg_id=%s): %s", username, tg_id, exc)


async def configure_scheduler_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Перечитать настройки времени и переустановить задания."""
    morning_time = await get_morning_broadcast_time()
    afternoon_time = await get_afternoon_reminder_time()

    scheduler.remove_all_jobs()

    scheduler.add_job(
        send_morning_prompt,
        trigger=_parse_time_to_cron(morning_time),
        args=[bot],
        id="morning_broadcast",
        replace_existing=True,
    )
    logger.info("Запланирована утренняя рассылка на %s", morning_time)

    scheduler.add_job(
        send_afternoon_reminder,
        trigger=_parse_time_to_cron(afternoon_time),
        args=[bot],
        id="afternoon_reminder",
        replace_existing=True,
    )
    logger.info("Запланировано дневное напоминание на %s", afternoon_time)


async def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Создать (при необходимости) и запустить планировщик.

    Возвращает экземпляр scheduler, чтобы main мог управлять его жизненным циклом.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=tz)

    await configure_scheduler_jobs(_scheduler, bot)

    if not _scheduler.running:
        _scheduler.start()
        logger.info("Планировщик запущен")

    return _scheduler


async def shutdown_scheduler(wait: bool = False) -> None:
    """Остановить планировщик, если он запущен."""
    if _scheduler and _scheduler.running:
        await asyncio.to_thread(_scheduler.shutdown, wait=wait)
        logger.info("Планировщик остановлен")

