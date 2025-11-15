"""Обработчик выбора формата работы."""
import logging
from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.database import get_user_by_tg_id, add_work_day, add_vacation
from bot.keyboards import WORK_FORMATS
from bot.utils.date_utils import (
    get_today_date,
    format_date_for_display,
    parse_date_range,
    generate_date_range
)

logger = logging.getLogger(__name__)
router = Router()

# Форматы, требующие диапазона дат
DATE_RANGE_FORMATS = ["Отпуск", "Болезнь", "Экспедиция"]

# Маппинг форматов на типы для таблицы vacations
FORMAT_TO_VACATION_TYPE = {
    "Отпуск": "vacation",
    "Болезнь": "sick",
    "Экспедиция": "expedition"
}


class WorkFormatStates(StatesGroup):
    """Состояния для выбора формата работы."""
    waiting_for_date_range = State()


@router.message(lambda message: message.text and message.text in WORK_FORMATS)
async def handle_work_format(message: Message, state: FSMContext):
    """Обработчик выбора формата работы."""
    user_id = message.from_user.id
    format_text = message.text
    
    logger.info(f"Обработка выбора формата работы: user_id={user_id}, format={format_text}")
    
    # Очищаем предыдущее состояние FSM, если оно было активно
    # Это позволяет корректно обработать случай, когда пользователь выбирает
    # другой формат во время ожидания диапазона дат
    current_state = await state.get_state()
    if current_state == WorkFormatStates.waiting_for_date_range:
        await state.clear()
        logger.info(f"Очищено предыдущее состояние FSM для user_id={user_id}")
    
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
    
    # Проверяем, требует ли формат диапазон дат
    if format_text in DATE_RANGE_FORMATS:
        # Сохраняем выбранный формат в FSM
        await state.update_data(selected_format=format_text)
        
        # Переходим в состояние ожидания диапазона дат
        await state.set_state(WorkFormatStates.waiting_for_date_range)
        
        # Запрашиваем диапазон дат
        await message.answer(
            f"📅 Укажите диапазон дат для формата \"{format_text}\":\n\n"
            f"Примеры:\n"
            f"• 01.01.2024 - 15.01.2024\n"
            f"• 01.01 - 15.01 (год будет текущим)\n"
            f"• 15.03.2024 - 20.03.2024",
            reply_markup=ReplyKeyboardRemove()
        )
        
        logger.info(f"Запрошен диапазон дат для формата: user_id={user_id}, format={format_text}")
        return
    
    # Если формат не требует диапазона, сохраняем как обычно (один день)
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
        
        # Завершаем состояние FSM (если оно было активно)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении формата работы: {e}", exc_info=True)
        await state.clear()
        await message.answer(
            "❌ Произошла ошибка при сохранении формата работы. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )


@router.message(WorkFormatStates.waiting_for_date_range)
async def handle_date_range(message: Message, state: FSMContext):
    """Обработчик ввода диапазона дат."""
    user_id = message.from_user.id
    date_range_str = message.text
    
    logger.info(f"Обработка диапазона дат: user_id={user_id}, range={date_range_str}")
    
    # Получаем сохранённый формат из FSM
    data = await state.get_data()
    selected_format = data.get('selected_format')
    
    if not selected_format:
        logger.error(f"Не найден выбранный формат в FSM для user_id={user_id}")
        await state.clear()
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, начните заново.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Валидация диапазона дат
    is_valid, error_msg, start_date, end_date = parse_date_range(date_range_str)
    
    if not is_valid:
        # Ошибка валидации - сообщаем и запрашиваем повторный ввод
        await message.answer(
            f"❌ {error_msg}\n\n"
            f"Пожалуйста, укажите диапазон дат ещё раз.\n\n"
            f"Примеры:\n"
            f"• 01.01.2024 - 15.01.2024\n"
            f"• 01.01 - 15.01\n"
            f"• 15.03.2024 - 20.03.2024"
        )
        logger.warning(f"Ошибка валидации диапазона дат: user_id={user_id}, error={error_msg}")
        return
    
    try:
        # Конвертируем даты в формат YYYY-MM-DD
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Получаем тип для таблицы vacations
        vacation_type = FORMAT_TO_VACATION_TYPE.get(selected_format, "vacation")
        
        # Сохраняем диапазон в таблицу vacations
        vacation_id = await add_vacation(
            tg_id=user_id,
            start_date=start_date_str,
            end_date=end_date_str,
            vacation_type=vacation_type
        )
        
        logger.info(
            f"Отпуск/болезнь/экспедиция сохранена: "
            f"user_id={user_id}, vacation_id={vacation_id}, "
            f"{start_date_str} - {end_date_str}, type={vacation_type}"
        )
        
        # Генерируем список всех дат в диапазоне
        date_list = generate_date_range(start_date, end_date)
        
        # Сохраняем каждую дату в work_days с выбранным форматом
        saved_dates = []
        for date_str in date_list:
            await add_work_day(user_id, date_str, selected_format)
            saved_dates.append(date_str)
        
        # Форматируем даты для отображения
        formatted_start = format_date_for_display(start_date_str)
        formatted_end = format_date_for_display(end_date_str)
        
        # Отправляем подтверждение
        await message.answer(
            f"✅ Формат работы сохранён:\n"
            f"📅 Период: {formatted_start} - {formatted_end}\n"
            f"💼 Формат: {selected_format}\n"
            f"📊 Дней: {len(saved_dates)}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        logger.info(
            f"Формат работы успешно сохранён для диапазона: "
            f"user_id={user_id}, format={selected_format}, "
            f"dates={len(saved_dates)}"
        )
        
        # Завершаем состояние FSM
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении диапазона дат: {e}", exc_info=True)
        await state.clear()
        await message.answer(
            "❌ Произошла ошибка при сохранении диапазона дат. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )

