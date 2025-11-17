"""Модуль для работы с базой данных."""
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz

from bot.config import (
    TIMEZONE,
    DEFAULT_ADMINS,
    DEFAULT_TEST_USERS,
    MORNING_BROADCAST_TIME,
    AFTERNOON_REMINDER_TIME,
)
from bot.utils.date_utils import get_today_date

logger = logging.getLogger(__name__)

DB_PATH = "bot_data.db"

# Часовой пояс
tz = pytz.timezone(TIMEZONE)

SETTING_MORNING_TIME = "morning_broadcast_time"
SETTING_AFTERNOON_TIME = "afternoon_reminder_time"

DEFAULT_TIME_SETTINGS = {
    SETTING_MORNING_TIME: MORNING_BROADCAST_TIME,
    SETTING_AFTERNOON_TIME: AFTERNOON_REMINDER_TIME,
}


def get_current_time() -> str:
    """Получить текущее время в часовом поясе Екатеринбурга."""
    return datetime.now(tz).isoformat()


async def init_db():
    """Инициализация базы данных."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'employee',
                active_flag INTEGER NOT NULL DEFAULT 1,
                consent_given INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        # Таблица рабочих дней
        await db.execute("""
            CREATE TABLE IF NOT EXISTS work_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (tg_id) REFERENCES users(tg_id),
                UNIQUE(tg_id, date)
            )
        """)
        
        # Таблица отпусков/болезней/экспедиций
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vacations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (tg_id) REFERENCES users(tg_id)
            )
        """)

        # Таблица настроек
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        await db.commit()
        logger.info("База данных инициализирована")

    await sync_default_time_settings()


async def get_setting(key: str) -> Optional[str]:
    """
    Получить значение настройки по ключу.

    Args:
        key: название настройки

    Returns:
        Значение настройки или None, если ключ не найден.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str) -> bool:
    """
    Сохранить значение настройки (создать или обновить).

    Args:
        key: название настройки
        value: значение настройки

    Returns:
        True если операция выполнена.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value)
        )
        await db.commit()
        logger.info("Настройка %s сохранена со значением %s", key, value)
        return True


async def sync_default_time_settings():
    """Убедиться, что базовые настройки времени присутствуют в БД и обновлены из .env."""
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in DEFAULT_TIME_SETTINGS.items():
            # Обновляем настройки из переменных окружения при каждом запуске
            await db.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value)
            )
        await db.commit()
        logger.info("Базовые настройки времени синхронизированы из переменных окружения")


async def _get_or_create_time_setting(key: str, default_value: str) -> str:
    """
    Получить настройку времени или создать с дефолтным значением.
    """
    value = await get_setting(key)
    if value is not None:
        return value
    await set_setting(key, default_value)
    return default_value


async def get_morning_broadcast_time() -> str:
    """Вернуть время утренней рассылки из БД или дефолтное значение."""
    return await _get_or_create_time_setting(
        SETTING_MORNING_TIME,
        MORNING_BROADCAST_TIME,
    )


async def get_afternoon_reminder_time() -> str:
    """Вернуть время дневного напоминания из БД или дефолтное значение."""
    return await _get_or_create_time_setting(
        SETTING_AFTERNOON_TIME,
        AFTERNOON_REMINDER_TIME,
    )


async def create_user(
    tg_id: int,
    username: Optional[str],
    name: str,
    role: str = 'employee',
    active: bool = True
) -> bool:
    """
    Создать нового пользователя.
    
    Args:
        tg_id: Telegram ID пользователя
        username: Username в Telegram (может быть None)
        name: Имя пользователя
        role: Роль ('employee' или 'admin')
        active: Активен ли пользователь (по умолчанию True)
    
    Returns:
        True если пользователь создан, False если уже существует
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            active_flag_value = 1 if active else 0
            await db.execute(
                """
                INSERT INTO users (tg_id, username, name, role, active_flag, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tg_id, username, name, role, active_flag_value, get_current_time())
            )
            await db.commit()
            logger.info(f"Пользователь создан: {name} (tg_id={tg_id}, role={role}, active={active}, active_flag={active_flag_value})")
            
            # Проверяем, что active_flag сохранился правильно
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT active_flag FROM users WHERE tg_id = ?",
                (tg_id,)
            ) as cursor:
                saved_row = await cursor.fetchone()
                if saved_row:
                    saved_active_flag = int(saved_row['active_flag']) if saved_row['active_flag'] is not None else 0
                    if saved_active_flag != active_flag_value:
                        logger.error(f"❌ ОШИБКА: active_flag не совпадает! Ожидалось={active_flag_value}, сохранено={saved_active_flag}")
                        # Исправляем
                        await db.execute(
                            "UPDATE users SET active_flag = ? WHERE tg_id = ?",
                            (active_flag_value, tg_id)
                        )
                        await db.commit()
                        logger.info(f"✅ Исправлен active_flag для пользователя tg_id={tg_id}")
            
            return True
    except aiosqlite.IntegrityError:
        logger.warning(f"Пользователь с tg_id={tg_id} уже существует")
        return False


async def get_user_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить пользователя по Telegram ID.
    
    Args:
        tg_id: Telegram ID пользователя
    
    Returns:
        Словарь с данными пользователя или None
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?",
            (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user_dict = dict(row)
                # Нормализуем active_flag и consent_given (могут быть int или str)
                if 'active_flag' in user_dict:
                    user_dict['active_flag'] = int(user_dict['active_flag']) if user_dict['active_flag'] is not None else 0
                if 'consent_given' in user_dict:
                    user_dict['consent_given'] = int(user_dict['consent_given']) if user_dict['consent_given'] is not None else 0
                return user_dict
            return None


async def is_user_exists(tg_id: int) -> bool:
    """
    Проверить, существует ли пользователь в БД (независимо от активности).
    
    Args:
        tg_id: Telegram ID пользователя
    
    Returns:
        True если пользователь существует в БД, False иначе
    """
    user = await get_user_by_tg_id(tg_id)
    return user is not None


async def is_user_registered(tg_id: int) -> bool:
    """
    Проверить, зарегистрирован ли пользователь и активен ли он.
    
    Args:
        tg_id: Telegram ID пользователя
    
    Returns:
        True если пользователь зарегистрирован и активен, False иначе
    """
    user = await get_user_by_tg_id(tg_id)
    if not user:
        return False
    # Проверяем, что пользователь активен (active_flag = 1)
    return bool(user.get('active_flag', 0))


async def is_user_admin(tg_id: int) -> bool:
    """
    Проверить, является ли пользователь администратором.
    
    Args:
        tg_id: Telegram ID пользователя
    
    Returns:
        True если пользователь является администратором, False иначе
    """
    user = await get_user_by_tg_id(tg_id)
    if not user:
        return False
    return user.get('role') == 'admin'


async def get_all_active_users() -> List[Dict[str, Any]]:
    """
    Получить всех активных пользователей.
    
    Returns:
        Список словарей с данными пользователей
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE active_flag = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_active_and_consented_users() -> List[Dict[str, Any]]:
    """
    Получить пользователей, которые активны и дали согласие.

    Returns:
        Список словарей с данными пользователей.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM users
            WHERE active_flag = 1 AND consent_given = 1
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_user_consent(tg_id: int, consent: bool) -> bool:
    """
    Обновить согласие пользователя на обработку данных.
    
    Args:
        tg_id: Telegram ID пользователя
        consent: Согласие (True/False)
    
    Returns:
        True если обновлено успешно
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET consent_given = ? WHERE tg_id = ?",
            (1 if consent else 0, tg_id)
        )
        await db.commit()
        logger.info(f"Согласие пользователя {tg_id} обновлено: {consent}")
        return True


async def update_user_active_flag(tg_id: int, active: bool) -> bool:
    """
    Обновить флаг активности пользователя (для увольнения).
    
    Args:
        tg_id: Telegram ID пользователя
        active: Активен (True) или уволен (False)
    
    Returns:
        True если обновлено успешно
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET active_flag = ? WHERE tg_id = ?",
            (1 if active else 0, tg_id)
        )
        await db.commit()
        logger.info(f"Статус активности пользователя {tg_id} изменён: {active}")
        return True


async def update_user_tg_id(old_tg_id: int, new_tg_id: int) -> bool:
    """
    Обновить tg_id пользователя (для замены временного ID на реальный).
    Использует удаление и создание новой записи, так как в SQLite нельзя
    напрямую обновить PRIMARY KEY.
    
    Args:
        old_tg_id: Старый Telegram ID
        new_tg_id: Новый Telegram ID
    
    Returns:
        True если обновлено успешно
    """
    logger.info(f"Обновление tg_id: {old_tg_id} -> {new_tg_id}")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Получаем данные старого пользователя
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?",
            (old_tg_id,)
        ) as cursor:
            old_user_row = await cursor.fetchone()
            if not old_user_row:
                logger.warning(f"❌ Пользователь с tg_id={old_tg_id} не найден для обновления")
                return False
            old_user = dict(old_user_row)
            logger.info(f"Найден пользователь для обновления: username=@{old_user.get('username')}, role={old_user.get('role')}, active_flag={old_user.get('active_flag')}")
        
        # Проверяем, не существует ли уже пользователь с новым tg_id
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?",
            (new_tg_id,)
        ) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                logger.warning(f"❌ Пользователь с tg_id={new_tg_id} уже существует, обновление невозможно")
                return False
        
        # Для тестовых пользователей принудительно устанавливаем active_flag=1
        from bot.config import DEFAULT_TEST_USERS
        final_active_flag = old_user['active_flag']
        if old_user.get('username') in DEFAULT_TEST_USERS:
            final_active_flag = 1
            logger.info(f"Для тестового пользователя @{old_user.get('username')} принудительно установлен active_flag=1")
        
        # Удаляем старую запись
        await db.execute("DELETE FROM users WHERE tg_id = ?", (old_tg_id,))
        logger.info(f"Удалена старая запись с tg_id={old_tg_id}")
        
        # Создаём новую запись с новым tg_id
        await db.execute(
            """
            INSERT INTO users (tg_id, username, name, role, active_flag, consent_given, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_tg_id,
                old_user['username'],
                old_user['name'],
                old_user['role'],
                final_active_flag,
                old_user['consent_given'],
                old_user['created_at']
            )
        )
        logger.info(f"Создана новая запись с tg_id={new_tg_id}, active_flag={final_active_flag}, role={old_user.get('role')}")
        
        # Обновляем связанные записи в work_days
        await db.execute(
            "UPDATE work_days SET tg_id = ? WHERE tg_id = ?",
            (new_tg_id, old_tg_id)
        )
        
        # Обновляем связанные записи в vacations
        await db.execute(
            "UPDATE vacations SET tg_id = ? WHERE tg_id = ?",
            (new_tg_id, old_tg_id)
        )
        
        await db.commit()
        logger.info(f"✅ tg_id пользователя успешно обновлён: {old_tg_id} -> {new_tg_id} (включая связанные записи)")
        return True


async def register_admin_if_needed(tg_id: int, username: Optional[str], name: str) -> bool:
    """
    Автоматически зарегистрировать администратора при первом входе.
    
    Проверяет, есть ли username в списке DEFAULT_ADMINS, и если есть,
    создаёт или обновляет запись пользователя с ролью admin.
    
    Args:
        tg_id: Telegram ID пользователя
        username: Username в Telegram (может быть None)
        name: Имя пользователя
    
    Returns:
        True если пользователь был зарегистрирован как админ, False иначе
    """
    if not username:
        return False
    
    from bot.config import DEFAULT_ADMINS
    
    if username not in DEFAULT_ADMINS:
        return False
    
    # Проверяем, есть ли уже запись с таким username (placeholder)
    existing_user = await get_user_by_username(username)
    
    if existing_user:
        # Если есть placeholder с отрицательным tg_id, обновляем его
        if existing_user['tg_id'] < 0:
            await update_user_tg_id(existing_user['tg_id'], tg_id)
            logger.info(f"Обновлён placeholder администратора @{username} с tg_id={tg_id}")
        # Если уже есть запись с правильным tg_id, ничего не делаем
        return True
    else:
        # Создаём новую запись администратора
        await create_user(
            tg_id=tg_id,
            username=username,
            name=name,
            role='admin'
        )
        logger.info(f"Создан новый администратор @{username} с tg_id={tg_id}")
        return True


async def add_work_day(tg_id: int, date: str, status: str) -> bool:
    """
    Добавить или обновить запись о рабочем дне.
    
    Args:
        tg_id: Telegram ID пользователя
        date: Дата в формате YYYY-MM-DD
        status: Статус работы
    
    Returns:
        True если добавлено/обновлено успешно
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO work_days (tg_id, date, status, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tg_id, date) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (tg_id, date, status, get_current_time())
        )
        await db.commit()
        logger.info(f"Рабочий день добавлен/обновлён: tg_id={tg_id}, date={date}, status={status}")
        return True


async def set_range_work_days(
    tg_id: int,
    start_date: str,
    end_date: str,
    status: str,
    max_days: int = 365
) -> bool:
    """
    Массово проставить статус в таблице work_days на диапазон дат.

    Args:
        tg_id: Telegram ID пользователя
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
        status: Статус для установки
        max_days: Максимальная длина диапазона (по умолчанию 365)

    Returns:
        True если операция выполнена успешно

    Raises:
        ValueError: если даты в неверном порядке или диапазон слишком велик
    """
    start_dt = datetime.fromisoformat(start_date).date()
    end_dt = datetime.fromisoformat(end_date).date()

    if start_dt > end_dt:
        raise ValueError("Дата начала диапазона не может быть позже даты окончания.")

    total_days = (end_dt - start_dt).days + 1
    if total_days > max_days:
        raise ValueError(f"Диапазон дат превышает допустимое значение {max_days} дней.")

    logger.info(
        "Массовое обновление work_days: tg_id=%s, %s -> %s, статус=%s, дней=%s",
        tg_id,
        start_date,
        end_date,
        status,
        total_days
    )

    async with aiosqlite.connect(DB_PATH) as db:
        current_date = start_dt
        while current_date <= end_dt:
            await db.execute(
                """
                INSERT INTO work_days (tg_id, date, status, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tg_id, date) DO UPDATE SET
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (tg_id, current_date.isoformat(), status, get_current_time())
            )
            current_date += timedelta(days=1)

        await db.commit()

    logger.info(
        "Диапазон work_days обновлён: tg_id=%s, %s -> %s, статус=%s",
        tg_id,
        start_date,
        end_date,
        status
    )
    return True


async def get_work_day(tg_id: int, date: str) -> Optional[Dict[str, Any]]:
    """
    Получить запись о рабочем дне.
    
    Args:
        tg_id: Telegram ID пользователя
        date: Дата в формате YYYY-MM-DD
    
    Returns:
        Словарь с данными или None
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM work_days WHERE tg_id = ? AND date = ?",
            (tg_id, date)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def has_user_answered_today(tg_id: int, date: str) -> bool:
    """
    Проверить, есть ли запись о рабочем дне для пользователя на указанную дату.
    
    Args:
        tg_id: Telegram ID пользователя
        date: Дата в формате YYYY-MM-DD
    
    Returns:
        True если запись существует, False иначе
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM work_days WHERE tg_id = ? AND date = ?",
            (tg_id, date)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_users_without_answer_today(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получить список активных сотрудников с согласием, у которых нет записи в work_days на указанную дату.
    
    Args:
        date: Дата в формате YYYY-MM-DD. Если не указана, используется текущая дата через get_today_date()
    
    Returns:
        Список словарей с данными пользователей, которые не ответили на указанную дату
    """
    # Если дата не указана, используем текущую дату
    if date is None:
        date = get_today_date()
    
    # Получаем всех активных пользователей с согласием
    all_active_users = await get_active_and_consented_users()
    
    # Фильтруем тех, у кого нет записи на указанную дату
    users_without_answer = []
    for user in all_active_users:
        tg_id = user["tg_id"]
        if not await has_user_answered_today(tg_id, date):
            users_without_answer.append(user)
    
    return users_without_answer


async def get_work_days(
    tg_id: int,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """
    Получить записи о рабочих днях за период.
    
    Args:
        tg_id: Telegram ID пользователя
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
    
    Returns:
        Список словарей с данными
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM work_days
            WHERE tg_id = ? AND date >= ? AND date <= ?
            ORDER BY date
            """,
            (tg_id, start_date, end_date)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_vacation(
    tg_id: int,
    start_date: str,
    end_date: str,
    vacation_type: str
) -> int:
    """
    Добавить запись об отпуске/болезни/экспедиции.
    
    Args:
        tg_id: Telegram ID пользователя
        start_date: Дата начала в формате YYYY-MM-DD
        end_date: Дата окончания в формате YYYY-MM-DD
        vacation_type: Тип ('vacation', 'sick', 'expedition')
    
    Returns:
        ID созданной записи
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO vacations (tg_id, start_date, end_date, type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tg_id, start_date, end_date, vacation_type, get_current_time())
        )
        await db.commit()
        vacation_id = cursor.lastrowid
        logger.info(
            f"Отпуск/болезнь/экспедиция добавлена: "
            f"tg_id={tg_id}, {start_date} - {end_date}, type={vacation_type}"
        )
        return vacation_id


async def get_vacations(tg_id: int) -> List[Dict[str, Any]]:
    """
    Получить все отпуска/болезни/экспедиции пользователя.
    
    Args:
        tg_id: Telegram ID пользователя
    
    Returns:
        Список словарей с данными
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM vacations WHERE tg_id = ? ORDER BY start_date DESC",
            (tg_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Получить пользователя по username.
    
    Args:
        username: Username в Telegram (без @)
    
    Returns:
        Словарь с данными пользователя или None
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                user_dict = dict(row)
                # Нормализуем active_flag и consent_given (могут быть int или str)
                if 'active_flag' in user_dict:
                    user_dict['active_flag'] = int(user_dict['active_flag']) if user_dict['active_flag'] is not None else 0
                if 'consent_given' in user_dict:
                    user_dict['consent_given'] = int(user_dict['consent_given']) if user_dict['consent_given'] is not None else 0
                return user_dict
            return None


async def create_default_admin():
    """Создать администраторов по умолчанию, если их нет."""
    for idx, admin_username in enumerate(DEFAULT_ADMINS):
        # Проверяем, существует ли уже админ с таким username
        admin = await get_user_by_username(admin_username)
        
        if not admin:
            # Создаём запись для будущего админа
            # tg_id = -(idx+1) - временный отрицательный ID, обновится при первом входе
            temp_tg_id = -(idx + 1)
            await create_user(
                tg_id=temp_tg_id,
                username=admin_username,
                name=admin_username,
                role='admin'
            )
            logger.info(f"Создан placeholder для администратора @{admin_username}")
    
    if DEFAULT_ADMINS:
        logger.warning(
            f"ВАЖНО: Пользователи с username из списка {DEFAULT_ADMINS} "
            "будут назначены администраторами при первом входе"
        )


async def create_default_test_users():
    """Создать тестовых пользователей по умолчанию, если их нет."""
    logger.info(f"Создание тестовых пользователей из списка: {DEFAULT_TEST_USERS}")
    for idx, test_username in enumerate(DEFAULT_TEST_USERS):
        # Проверяем, существует ли уже пользователь с таким username
        existing_user = await get_user_by_username(test_username)
        logger.info(f"Проверка пользователя @{test_username}: существующий пользователь = {existing_user is not None}")
        
        if not existing_user:
            # Создаём placeholder для будущего пользователя
            # tg_id = -(idx+100) - временный отрицательный ID, обновится при первом входе
            temp_tg_id = -(idx + 100)
            logger.info(f"Создание placeholder для @{test_username} с temp_tg_id={temp_tg_id}")
            success = await create_user(
                tg_id=temp_tg_id,
                username=test_username,
                name=test_username,
                role='employee',
                active=True  # Активный для тестирования
            )
            if success:
                # Проверяем, что пользователь создан с правильным active_flag
                created_user = await get_user_by_tg_id(temp_tg_id)
                if created_user:
                    active_flag = created_user.get('active_flag', 0)
                    logger.info(f"✅ Создан placeholder для тестового пользователя @{test_username} с tg_id={temp_tg_id}, active_flag={active_flag}")
                    if not active_flag:
                        logger.error(f"❌ ОШИБКА: placeholder создан с active_flag=0! Исправляю...")
                        await update_user_active_flag(temp_tg_id, True)
                        logger.info(f"✅ Исправлен active_flag для @{test_username}")
                else:
                    logger.warning(f"❌ Не удалось найти созданного пользователя @{test_username}")
            else:
                logger.warning(f"❌ Не удалось создать placeholder для тестового пользователя @{test_username}")
        else:
            logger.info(f"Пользователь @{test_username} уже существует с tg_id={existing_user.get('tg_id')}")
    
    if DEFAULT_TEST_USERS:
        logger.info(
            f"Завершено создание placeholder'ов для тестовых пользователей: {DEFAULT_TEST_USERS}. "
            "Они будут активны после первого входа и обновления tg_id."
        )


async def fix_test_users_active_flag():
    """Исправить active_flag для всех тестовых пользователей (установить в 1)."""
    from bot.config import DEFAULT_TEST_USERS
    for test_username in DEFAULT_TEST_USERS:
        user = await get_user_by_username(test_username)
        if user:
            if not user.get('active_flag', 0):
                await update_user_active_flag(user['tg_id'], True)
                logger.info(f"✅ Исправлен active_flag=1 для тестового пользователя @{test_username} (tg_id={user['tg_id']})")
            else:
                logger.info(f"Тестовый пользователь @{test_username} уже имеет active_flag=1")

