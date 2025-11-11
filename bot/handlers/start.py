"""Обработчик команды /start."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Я помогу отслеживать формат работы сотрудников.\n"
        "Используйте /start для начала работы."
    )
