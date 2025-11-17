"""Тесты для модуля bot.scheduler."""
from datetime import datetime
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytz
from apscheduler.triggers.cron import CronTrigger

from bot.config import TIMEZONE
from bot.scheduler import (
    _parse_time_to_cron,
    configure_scheduler_jobs,
    send_morning_prompt,
    send_afternoon_reminder,
    start_scheduler,
    shutdown_scheduler,
)


tz = pytz.timezone(TIMEZONE)


class DummyScheduler:
    """Простейший шедулер для проверки add_job/remove_all_jobs."""

    def __init__(self):
        self.removed = False
        self.jobs: List[dict[str, Any]] = []

    def remove_all_jobs(self) -> None:
        self.removed = True

    def add_job(self, func, trigger, args=None, id=None, replace_existing=False):
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "args": args or [],
                "id": id,
                "replace_existing": replace_existing,
            }
        )


def _next_fire_components(trigger: CronTrigger) -> tuple[int, int]:
    """Вспомогательная функция: определить часы и минуты следующего срабатывания."""
    base = tz.localize(datetime(2025, 1, 1, 0, 0))
    next_fire = trigger.get_next_fire_time(previous_fire_time=None, now=base)
    return next_fire.hour, next_fire.minute


def test_parse_time_to_cron_valid_time():
    """Корректная строка времени возвращает CronTrigger с нужными часами и минутами."""
    trigger = _parse_time_to_cron("06:45")
    assert isinstance(trigger, CronTrigger)
    hour, minute = _next_fire_components(trigger)
    assert (hour, minute) == (6, 45)


@pytest.mark.parametrize("bad_value", ["", "25:00", "08-00", "12", "text"])
def test_parse_time_to_cron_invalid_format(bad_value):
    """Некорректная строка приводит к ValueError."""
    with pytest.raises(ValueError):
        _parse_time_to_cron(bad_value)


@pytest.mark.asyncio
async def test_send_morning_prompt_sends_messages(monkeypatch, mock_bot):
    """Сообщения отправляются всем активным пользователям с согласием."""
    users = [{"tg_id": 1}, {"tg_id": 2}]
    monkeypatch.setattr(
        "bot.scheduler.get_active_and_consented_users",
        AsyncMock(return_value=users),
    )
    keyboard = MagicMock(name="keyboard")
    monkeypatch.setattr(
        "bot.scheduler.get_work_format_keyboard",
        MagicMock(return_value=keyboard),
    )

    await send_morning_prompt(mock_bot)

    assert mock_bot.send_message.await_count == len(users)
    for call, user in zip(mock_bot.send_message.await_args_list, users, strict=True):
        args, kwargs = call
        assert args[0] == user["tg_id"]
        assert kwargs["reply_markup"] == keyboard
        assert "Доброе утро" in args[1]


@pytest.mark.asyncio
async def test_send_morning_prompt_skips_when_no_users(monkeypatch, mock_bot):
    """Если нет пользователей, сообщение не отправляется."""
    monkeypatch.setattr(
        "bot.scheduler.get_active_and_consented_users",
        AsyncMock(return_value=[]),
    )

    await send_morning_prompt(mock_bot)

    assert mock_bot.send_message.await_count == 0


@pytest.mark.asyncio
async def test_send_morning_prompt_handles_errors(monkeypatch, mock_bot, caplog):
    """Ошибки отправки логируются и не прерывают цикл."""
    users = [{"tg_id": 1}, {"tg_id": 2}]
    monkeypatch.setattr(
        "bot.scheduler.get_active_and_consented_users",
        AsyncMock(return_value=users),
    )
    monkeypatch.setattr(
        "bot.scheduler.get_work_format_keyboard",
        MagicMock(return_value="keyboard"),
    )
    mock_bot.send_message.side_effect = [
        RuntimeError("boom"),
        None,
    ]

    with caplog.at_level("ERROR"):
        await send_morning_prompt(mock_bot)

    assert mock_bot.send_message.await_count == len(users)
    assert "Не удалось отправить утреннее сообщение" in caplog.text


@pytest.mark.asyncio
async def test_send_afternoon_reminder_sends_messages(monkeypatch, mock_bot):
    """Сообщения отправляются только пользователям, которые не ответили."""
    users = [{"tg_id": 1, "username": "user1"}, {"tg_id": 2, "username": "user2"}]
    monkeypatch.setattr(
        "bot.scheduler.get_users_without_answer_today",
        AsyncMock(return_value=users),
    )
    keyboard = MagicMock(name="keyboard")
    monkeypatch.setattr(
        "bot.scheduler.get_work_format_keyboard",
        MagicMock(return_value=keyboard),
    )

    await send_afternoon_reminder(mock_bot)

    assert mock_bot.send_message.await_count == len(users)
    for call, user in zip(mock_bot.send_message.await_args_list, users, strict=True):
        args, kwargs = call
        assert args[0] == user["tg_id"]
        assert kwargs["reply_markup"] == keyboard
        assert "Напоминание" in args[1]


@pytest.mark.asyncio
async def test_send_afternoon_reminder_skips_when_all_answered(monkeypatch, mock_bot):
    """Если все ответили, сообщение не отправляется."""
    monkeypatch.setattr(
        "bot.scheduler.get_users_without_answer_today",
        AsyncMock(return_value=[]),
    )

    await send_afternoon_reminder(mock_bot)

    assert mock_bot.send_message.await_count == 0


@pytest.mark.asyncio
async def test_send_afternoon_reminder_handles_errors(monkeypatch, mock_bot, caplog):
    """Ошибки отправки логируются и не прерывают цикл."""
    users = [{"tg_id": 1, "username": "user1"}, {"tg_id": 2, "username": "user2"}]
    monkeypatch.setattr(
        "bot.scheduler.get_users_without_answer_today",
        AsyncMock(return_value=users),
    )
    monkeypatch.setattr(
        "bot.scheduler.get_work_format_keyboard",
        MagicMock(return_value="keyboard"),
    )
    mock_bot.send_message.side_effect = [
        RuntimeError("boom"),
        None,
    ]

    with caplog.at_level("ERROR"):
        await send_afternoon_reminder(mock_bot)

    assert mock_bot.send_message.await_count == len(users)
    assert "Не удалось отправить дневное напоминание" in caplog.text


@pytest.mark.asyncio
async def test_configure_scheduler_jobs(monkeypatch, mock_bot):
    """Планировщик очищает старые задания и создаёт два cron-триггера."""
    scheduler = DummyScheduler()
    monkeypatch.setattr(
        "bot.scheduler.get_morning_broadcast_time",
        AsyncMock(return_value="07:10"),
    )
    monkeypatch.setattr(
        "bot.scheduler.get_afternoon_reminder_time",
        AsyncMock(return_value="13:25"),
    )

    await configure_scheduler_jobs(scheduler, mock_bot)

    assert scheduler.removed is True
    assert [job["id"] for job in scheduler.jobs] == [
        "morning_broadcast",
        "afternoon_reminder",
    ]

    morning_job, afternoon_job = scheduler.jobs
    assert morning_job["func"] is send_morning_prompt
    assert afternoon_job["func"] is send_afternoon_reminder
    assert morning_job["args"] == [mock_bot]
    assert afternoon_job["args"] == [mock_bot]
    assert morning_job["replace_existing"] is True

    assert isinstance(morning_job["trigger"], CronTrigger)
    assert isinstance(afternoon_job["trigger"], CronTrigger)

    assert _next_fire_components(morning_job["trigger"]) == (7, 10)
    assert _next_fire_components(afternoon_job["trigger"]) == (13, 25)


class FakeAsyncScheduler:
    """Минималистичный AsyncIOScheduler для тестов start_scheduler."""

    def __init__(self, timezone):
        self.timezone = timezone
        self.running = False
        self.started = False

    def start(self):
        self.running = True
        self.started = True


@pytest.mark.asyncio
async def test_start_scheduler_initializes_once(monkeypatch, mock_bot):
    """start_scheduler создаёт планировщик и запускает его один раз."""
    created = {}

    def factory(timezone):
        scheduler = FakeAsyncScheduler(timezone)
        created["scheduler"] = scheduler
        return scheduler

    monkeypatch.setattr("bot.scheduler.AsyncIOScheduler", factory)
    configure_mock = AsyncMock()
    monkeypatch.setattr("bot.scheduler.configure_scheduler_jobs", configure_mock)
    monkeypatch.setattr("bot.scheduler._scheduler", None)

    scheduler_instance = await start_scheduler(mock_bot)

    assert scheduler_instance is created["scheduler"]
    assert scheduler_instance.running is True
    configure_mock.assert_awaited_once_with(scheduler_instance, mock_bot)


@pytest.mark.asyncio
async def test_shutdown_scheduler_calls_underlying(monkeypatch):
    """shutdown_scheduler вызывает shutdown у работающего планировщика."""
    class ShutdownTracker:
        def __init__(self):
            self.running = True

        def shutdown(self, wait=True):
            self.wait = wait

    tracker = ShutdownTracker()
    monkeypatch.setattr("bot.scheduler._scheduler", tracker)
    to_thread_mock = AsyncMock()
    monkeypatch.setattr("bot.scheduler.asyncio.to_thread", to_thread_mock)

    await shutdown_scheduler(wait=False)

    to_thread_mock.assert_awaited_once()
    args, kwargs = to_thread_mock.await_args
    assert getattr(args[0], "__self__", None) is tracker
    assert kwargs["wait"] is False


@pytest.mark.asyncio
async def test_shutdown_scheduler_noop_when_not_running(monkeypatch):
    """Если планировщик не запущен, shutdown ничего не делает."""
    tracker = MagicMock()
    tracker.running = False
    monkeypatch.setattr("bot.scheduler._scheduler", tracker)
    to_thread_mock = AsyncMock()
    monkeypatch.setattr("bot.scheduler.asyncio.to_thread", to_thread_mock)

    await shutdown_scheduler(wait=True)

    to_thread_mock.assert_not_called()

