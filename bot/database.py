"""Модуль для работы с базой данных."""
import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import pytz

from bot.config import TIMEZONE

logger = logging.getLogger(__name__)

DB_PATH = "bot_data.db"

# Часовой пояс
tz = pytz.timezone(TIMEZONE)


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
        
        await db.commit()
        logger.info("База данных инициализирована")


async def create_user(
    tg_id: int,
    username: Optional[str],
    name: str,
    role: str = 'employee'
) -> bool:
    """
    Создать нового пользователя.
    
    Args:
        tg_id: Telegram ID пользователя
        username: Username в Telegram (может быть None)
        name: Имя пользователя
        role: Роль ('employee' или 'admin')
    
    Returns:
        True если пользователь создан, False если уже существует
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (tg_id, username, name, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tg_id, username, name, role, get_current_time())
            )
            await db.commit()
            logger.info(f"Пользователь создан: {name} (tg_id={tg_id}, role={role})")
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
            return dict(row) if row else None


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


async def create_default_admin():
    """Создать администратора по умолчанию (@mirvien), если его нет."""
    # Проверяем, существует ли уже админ
    admin = await get_user_by_tg_id(0)  # Временный ID, будет заменён при первом входе
    
    if not admin:
        # Создаём запись для будущего админа
        # tg_id=0 - временный, обновится при первом входе пользователя @mirvien
        logger.info("Создан placeholder для администратора @mirvien")
        logger.warning(
            "ВАЖНО: Первый пользователь с username 'mirvien' "
            "будет назначен администратором"
        )

