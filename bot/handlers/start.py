"""Обработчик команды /start."""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from bot.database import get_user_by_tg_id, update_user_consent, register_admin_if_needed
from bot.keyboards import get_consent_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    logger.info(f"Обработка /start для user_id={user_id}, username=@{username}")
    
    # Пытаемся автоматически зарегистрировать администратора
    admin_registered = False
    if username:
        admin_registered = await register_admin_if_needed(user_id, username, name)
        logger.info(f"Попытка регистрации админа @{username}: {admin_registered}")
    
    # Пытаемся обновить tg_id тестового пользователя, если он есть
    if username and not admin_registered:
        from bot.database import get_user_by_username, update_user_tg_id
        test_user = await get_user_by_username(username)
        logger.info(f"Поиск тестового пользователя @{username}: {test_user is not None}")
        if test_user:
            logger.info(f"Найден тестовый пользователь: tg_id={test_user.get('tg_id')}, active={test_user.get('active_flag')}")
        if test_user and test_user['tg_id'] < 0:
            # Обновляем placeholder тестового пользователя
            old_tg_id = test_user['tg_id']
            old_active_flag = test_user.get('active_flag', 0)
            logger.info(f"Обновление placeholder: old_tg_id={old_tg_id}, old_active_flag={old_active_flag}")
            success = await update_user_tg_id(old_tg_id, user_id)
            if success:
                logger.info(f"✅ Обновлён placeholder тестового пользователя @{username} с tg_id={old_tg_id} на {user_id}")
                # Проверяем, что active_flag сохранился, и при необходимости исправляем
                updated_user = await get_user_by_tg_id(user_id)
                if updated_user:
                    logger.info(f"Проверка после обновления: active_flag={updated_user.get('active_flag')}, должен быть={old_active_flag}")
                    # Для тестовых пользователей принудительно устанавливаем active_flag=1
                    from bot.config import DEFAULT_TEST_USERS
                    if username in DEFAULT_TEST_USERS and not updated_user.get('active_flag'):
                        from bot.database import update_user_active_flag
                        await update_user_active_flag(user_id, True)
                        logger.info(f"✅ Принудительно установлен active_flag=1 для тестового пользователя @{username}")
                        # Обновляем данные пользователя
                        updated_user = await get_user_by_tg_id(user_id)
                    if updated_user.get('active_flag') != old_active_flag and old_active_flag:
                        logger.warning(f"⚠️ active_flag изменился при обновлении! Было={old_active_flag}, стало={updated_user.get('active_flag')}")
            else:
                logger.warning(f"❌ Не удалось обновить placeholder тестового пользователя @{username}")
    
    # Получаем информацию о пользователе (после возможного обновления)
    user = await get_user_by_tg_id(user_id)
    logger.info(f"Пользователь найден по tg_id={user_id}: {user is not None}")
    if user:
        logger.info(f"Данные пользователя: active={user.get('active_flag')}, consent={user.get('consent_given')}, role={user.get('role')}")
    
    # Если пользователь не зарегистрирован и не является админом - сразу блокируем
    if not user and not admin_registered:
        logger.warning(f"❌ Доступ закрыт для user_id={user_id}, username=@{username} - пользователь не найден")
        await message.answer(
            "🚫 Доступ закрыт.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Если пользователь всё ещё не найден после попытки регистрации админа
    if not user:
        user = await get_user_by_tg_id(user_id)
    
    # Если пользователь не найден - блокируем
    if not user:
        await message.answer(
            "🚫 Доступ закрыт.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем, дал ли пользователь согласие
    if not user.get('consent_given', 0):
        # Запрашиваем согласие у всех зарегистрированных пользователей (включая неактивных)
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для работы с ботом необходимо дать согласие на обработку персональных данных.\n\n"
            "Вы согласны на обработку ваших персональных данных?",
            reply_markup=get_consent_keyboard()
        )
        return
    
    # Проверяем, активен ли пользователь (уволенные сотрудники не могут использовать бота)
    if not user.get('active_flag', 0):
        await message.answer(
            "🚫 Доступ закрыт.\n\n"
            "Ваш аккаунт деактивирован.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Пользователь активен и дал согласие
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Я помогу отслеживать формат работы сотрудников.\n"
        "Используйте команды бота для работы.",
        reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру, если она была
    )


@router.message(lambda message: message.text in ["✅ Да, согласен", "❌ Нет, не согласен"])
async def handle_consent(message: Message):
    """Обработчик ответа на запрос согласия."""
    user_id = message.from_user.id
    user = await get_user_by_tg_id(user_id)
    
    if not user:
        await message.answer(
            "🚫 Доступ закрыт.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if message.text == "✅ Да, согласен":
        # Сохраняем согласие
        await update_user_consent(user_id, True)
        
        # Проверяем, активен ли пользователь
        if not user.get('active_flag', 0):
            await message.answer(
                "✅ Спасибо! Согласие на обработку персональных данных получено.\n\n"
                "🚫 Ваш аккаунт деактивирован. Обратитесь к администратору.",
                reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру
            )
            return
        
        await message.answer(
            "✅ Спасибо! Согласие на обработку персональных данных получено.\n\n"
            "Теперь вы можете использовать бота для работы.",
            reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру
        )
    else:
        # Пользователь не дал согласие - блокируем доступ
        await message.answer(
            "🚫 Доступ закрыт.",
            reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру
        )
