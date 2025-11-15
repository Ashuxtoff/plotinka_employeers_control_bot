"""Обработчик выбора формата работы."""
import logging
from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove

from bot.database import get_user_by_tg_id, add_work_day
from bot.keyboards import WORK_FORMATS
from bot.utils.date_utils import get_today_date, format_date_for_display

logger = logging.getLogger(__name__)
router = Router()


@router.message(lambda message: message.text and message.text in WORK_FORMATS)
async def handle_work_format(message: Message):
    """Обработчик выбора формата работы."""
    user_id = message.from_user.id
    format_text = message.text
    
    logger.info(f"Обработка выбора формата работы: user_id={user_id}, format={format_text}")
    
    # Получаем информацию о пользователе
    user = await get_user_by_tg_id(user_id)
    
    if not user:
        logger.warning(f"Пользователь не найден: user_id={user_id}")
        await message.answer(
            "🚫 Доступ закрыт.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем, дал ли пользователь согласие
    if not user.get('consent_given', 0):
        await message.answer(
            "⚠️ Для работы с ботом необходимо дать согласие на обработку персональных данных.\n"
            "Используйте команду /start для продолжения.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем, активен ли пользователь
    if not user.get('active_flag', 0):
        await message.answer(
            "🚫 Доступ закрыт.\n\n"
            "Ваш аккаунт деактивирован.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Получаем текущую дату
    today = get_today_date()
    
    try:
        # Сохраняем выбор в базу данных
        await add_work_day(user_id, today, format_text)
        
        # Форматируем дату для отображения
        formatted_date = format_date_for_display(today)
        
        # Отправляем подтверждение
        await message.answer(
            f"✅ Формат работы сохранён:\n"
            f"📅 Дата: {formatted_date}\n"
            f"💼 Формат: {format_text}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        logger.info(f"Формат работы успешно сохранён: user_id={user_id}, date={today}, format={format_text}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении формата работы: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при сохранении формата работы. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )

