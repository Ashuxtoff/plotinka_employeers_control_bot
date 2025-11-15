"""Обработчик команды /register для регистрации сотрудников."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import is_user_admin, create_user, get_user_by_tg_id, get_user_by_username

router = Router()


@router.message(Command("register"))
async def cmd_register(message: Message):
    """Обработчик команды /register для добавления сотрудника."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_user_admin(user_id):
        await message.answer("❌ Доступ запрещён. Только администраторы могут регистрировать сотрудников.")
        return
    
    # Парсим команду: /register @username или /register username
    command_parts = message.text.split()
    
    if len(command_parts) < 2:
        await message.answer(
            "📝 Регистрация сотрудника\n\n"
            "Использование: /register @username или /register username\n\n"
            "Пример: /register @employee1"
        )
        return
    
    # Извлекаем username (убираем @ если есть)
    username = command_parts[1].lstrip('@')
    
    if not username:
        await message.answer("❌ Ошибка: не указан username.")
        return
    
    # Проверяем, существует ли уже пользователь с таким username
    existing_user = await get_user_by_username(username)
    if existing_user:
        await message.answer(
            f"⚠️ Пользователь @{username} уже зарегистрирован.\n"
            f"Роль: {existing_user['role']}\n"
            f"Активен: {'Да' if existing_user['active_flag'] else 'Нет'}"
        )
        return
    
    # Пользователь должен сначала написать боту, чтобы мы могли получить его tg_id
    await message.answer(
        f"📝 Для регистрации сотрудника @{username}:\n\n"
        f"1. Попросите пользователя @{username} написать боту команду /start\n"
        f"2. После этого используйте команду: /register_by_id <tg_id>\n\n"
        f"Или используйте команду /register_by_username @{username} после того, "
        f"как пользователь напишет боту."
    )


@router.message(Command("register_by_username"))
async def cmd_register_by_username(message: Message):
    """Обработчик команды /register_by_username для добавления сотрудника по username."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_user_admin(user_id):
        await message.answer("❌ Доступ запрещён. Только администраторы могут регистрировать сотрудников.")
        return
    
    # Парсим команду: /register_by_username @username
    command_parts = message.text.split()
    
    if len(command_parts) < 2:
        await message.answer(
            "📝 Регистрация сотрудника по username\n\n"
            "Использование: /register_by_username @username\n\n"
            "Пример: /register_by_username @employee1\n\n"
            "Примечание: пользователь должен сначала написать боту /start, "
            "чтобы его данные были доступны."
        )
        return
    
    # Извлекаем username (убираем @ если есть)
    username = command_parts[1].lstrip('@')
    
    if not username:
        await message.answer("❌ Ошибка: не указан username.")
        return
    
    # Ищем пользователя по username
    existing_user = await get_user_by_username(username)
    
    if not existing_user:
        await message.answer(
            f"❌ Пользователь @{username} не найден.\n\n"
            f"Попросите пользователя написать боту команду /start, "
            f"чтобы его данные стали доступны."
        )
        return
    
    # Проверяем, не зарегистрирован ли уже как активный сотрудник
    if existing_user['active_flag']:
        await message.answer(
            f"⚠️ Пользователь @{username} уже зарегистрирован и активен.\n"
            f"Роль: {existing_user['role']}\n"
            f"tg_id: {existing_user['tg_id']}"
        )
        return
    
    # Активируем пользователя
    from bot.database import update_user_active_flag
    await update_user_active_flag(existing_user['tg_id'], True)
    
    await message.answer(
        f"✅ Пользователь @{username} успешно зарегистрирован как сотрудник.\n"
        f"Роль: {existing_user['role']}\n"
        f"tg_id: {existing_user['tg_id']}"
    )


@router.message(Command("register_by_id"))
async def cmd_register_by_id(message: Message):
    """Обработчик команды /register_by_id для добавления сотрудника по tg_id."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if not await is_user_admin(user_id):
        await message.answer("❌ Доступ запрещён. Только администраторы могут регистрировать сотрудников.")
        return
    
    # Парсим команду: /register_by_id <tg_id> <username> <name>
    command_parts = message.text.split()
    
    if len(command_parts) < 4:
        await message.answer(
            "📝 Регистрация сотрудника по ID\n\n"
            "Использование: /register_by_id <tg_id> <username> <имя>\n\n"
            "Пример: /register_by_id 123456789 employee1 Иван Иванов"
        )
        return
    
    try:
        new_tg_id = int(command_parts[1])
    except ValueError:
        await message.answer("❌ Ошибка: tg_id должен быть числом.")
        return
    
    new_username = command_parts[2].lstrip('@')
    new_name = ' '.join(command_parts[3:])
    
    # Проверяем, существует ли уже пользователь с таким tg_id
    existing_user = await get_user_by_tg_id(new_tg_id)
    if existing_user:
        if existing_user['active_flag']:
            await message.answer(
                f"⚠️ Пользователь с tg_id={new_tg_id} уже зарегистрирован и активен.\n"
                f"Username: @{existing_user.get('username', 'не указан')}\n"
                f"Роль: {existing_user['role']}"
            )
        else:
            # Активируем существующего пользователя
            from bot.database import update_user_active_flag
            await update_user_active_flag(new_tg_id, True)
            await message.answer(
                f"✅ Пользователь с tg_id={new_tg_id} активирован.\n"
                f"Username: @{existing_user.get('username', 'не указан')}\n"
                f"Роль: {existing_user['role']}"
            )
        return
    
    # Создаём нового пользователя
    success = await create_user(
        tg_id=new_tg_id,
        username=new_username,
        name=new_name,
        role='employee'
    )
    
    if success:
        await message.answer(
            f"✅ Сотрудник успешно зарегистрирован!\n\n"
            f"tg_id: {new_tg_id}\n"
            f"Username: @{new_username}\n"
            f"Имя: {new_name}\n"
            f"Роль: employee"
        )
    else:
        await message.answer("❌ Ошибка при регистрации сотрудника. Возможно, пользователь уже существует.")

