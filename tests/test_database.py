"""Тесты для модуля bot.database (работа с work_days)."""
import pytest

from bot.database import (
    create_user,
    set_range_work_days,
    get_work_days,
    add_work_day
)


USER_ID = 12345
USERNAME = "test_user"
NAME = "Test User"


@pytest.fixture
async def seeded_user(test_db):
    """Создаёт пользователя в тестовой БД для дальнейших проверок."""
    await create_user(
        tg_id=USER_ID,
        username=USERNAME,
        name=NAME,
        role="employee",
        active=True
    )
    return USER_ID


@pytest.mark.asyncio
async def test_set_range_work_days_inserts_full_range(seeded_user):
    """Диапазон дат целиком сохраняется с нужным статусом."""
    start_date = "2025-01-01"
    end_date = "2025-01-03"
    status = "Отпуск"

    await set_range_work_days(seeded_user, start_date, end_date, status)

    work_days = await get_work_days(seeded_user, start_date, end_date)
    assert len(work_days) == 3
    assert all(row["status"] == status for row in work_days)
    assert {row["date"] for row in work_days} == {"2025-01-01", "2025-01-02", "2025-01-03"}


@pytest.mark.asyncio
async def test_set_range_work_days_updates_existing_records(seeded_user):
    """Существующие записи обновляются, новые добавляются."""
    await add_work_day(seeded_user, "2025-02-01", "Офис")

    await set_range_work_days(
        tg_id=seeded_user,
        start_date="2025-02-01",
        end_date="2025-02-03",
        status="Болезнь"
    )

    work_days = await get_work_days(seeded_user, "2025-02-01", "2025-02-03")
    assert len(work_days) == 3
    assert all(row["status"] == "Болезнь" for row in work_days)


@pytest.mark.asyncio
async def test_set_range_work_days_invalid_order_raises(seeded_user):
    """Дата начала позже окончания -> ValueError и никаких записей."""
    with pytest.raises(ValueError):
        await set_range_work_days(
            seeded_user,
            start_date="2025-03-05",
            end_date="2025-03-01",
            status="Экспедиция"
        )

    work_days = await get_work_days(seeded_user, "2025-03-01", "2025-03-05")
    assert work_days == []


@pytest.mark.asyncio
async def test_set_range_work_days_exceeds_limit_raises(seeded_user):
    """Выход за max_days вызывает ValueError и ничего не сохраняет."""
    with pytest.raises(ValueError):
        await set_range_work_days(
            seeded_user,
            start_date="2025-04-01",
            end_date="2025-04-05",
            status="Отпуск",
            max_days=2
        )

    work_days = await get_work_days(seeded_user, "2025-04-01", "2025-04-05")
    assert work_days == []
"""Тесты для модуля database."""
import pytest
import aiosqlite
from datetime import date
from unittest.mock import patch
from bot.database import (
    init_db,
    create_user,
    get_user_by_tg_id,
    get_user_by_username,
    get_all_active_users,
    update_user_consent,
    update_user_active_flag,
    add_work_day,
    get_work_day,
    get_work_days,
    add_vacation,
    get_vacations,
    is_user_registered,
    is_user_exists,
    is_user_admin,
    update_user_tg_id,
    register_admin_if_needed,
)


@pytest.mark.asyncio
async def test_init_db(test_db):
    """Тест инициализации БД."""
    # БД уже инициализирована в фикстуре test_db
    async with aiosqlite.connect(test_db) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
            assert "users" in tables
            assert "work_days" in tables
            assert "vacations" in tables


@pytest.mark.asyncio
async def test_create_user(test_db, sample_user_data):
    """Тест создания пользователя."""
    success = await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    assert success is True
    
    # Проверяем, что пользователь создан
    user = await get_user_by_tg_id(sample_user_data["tg_id"])
    assert user is not None
    assert user["username"] == sample_user_data["username"]
    assert user["name"] == sample_user_data["name"]
    assert user["role"] == sample_user_data["role"]
    assert user["active_flag"] == 1


@pytest.mark.asyncio
async def test_create_duplicate_user(test_db, sample_user_data):
    """Тест создания дубликата пользователя."""
    # Создаём пользователя первый раз
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Пытаемся создать того же пользователя второй раз
    success = await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name="Another Name",
        role="admin"
    )
    assert success is False


@pytest.mark.asyncio
async def test_get_user_by_tg_id(test_db, sample_user_data):
    """Тест получения пользователя по tg_id."""
    # Создаём пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Получаем пользователя
    user = await get_user_by_tg_id(sample_user_data["tg_id"])
    assert user is not None
    assert user["tg_id"] == sample_user_data["tg_id"]
    
    # Проверяем несуществующего пользователя
    user = await get_user_by_tg_id(999999999)
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_username(test_db, sample_user_data):
    """Тест получения пользователя по username."""
    # Создаём пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Получаем пользователя
    user = await get_user_by_username(sample_user_data["username"])
    assert user is not None
    assert user["username"] == sample_user_data["username"]
    
    # Проверяем несуществующего пользователя
    user = await get_user_by_username("nonexistent")
    assert user is None


@pytest.mark.asyncio
async def test_get_all_active_users(test_db, sample_user_data, sample_admin_data):
    """Тест получения всех активных пользователей."""
    # Создаём активного пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"],
        active=True
    )
    
    # Создаём активного администратора
    await create_user(
        tg_id=sample_admin_data["tg_id"],
        username=sample_admin_data["username"],
        name=sample_admin_data["name"],
        role=sample_admin_data["role"],
        active=True
    )
    
    # Создаём неактивного пользователя
    await create_user(
        tg_id=111111111,
        username="inactive",
        name="Inactive User",
        role="employee",
        active=False
    )
    
    # Получаем всех активных пользователей
    active_users = await get_all_active_users()
    assert len(active_users) == 2
    tg_ids = [u["tg_id"] for u in active_users]
    assert sample_user_data["tg_id"] in tg_ids
    assert sample_admin_data["tg_id"] in tg_ids
    assert 111111111 not in tg_ids


@pytest.mark.asyncio
async def test_update_user_consent(test_db, sample_user_data):
    """Тест обновления согласия пользователя."""
    # Создаём пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Обновляем согласие
    await update_user_consent(sample_user_data["tg_id"], True)
    
    # Проверяем
    user = await get_user_by_tg_id(sample_user_data["tg_id"])
    assert user["consent_given"] == 1
    
    # Обновляем обратно
    await update_user_consent(sample_user_data["tg_id"], False)
    user = await get_user_by_tg_id(sample_user_data["tg_id"])
    assert user["consent_given"] == 0


@pytest.mark.asyncio
async def test_update_user_active_flag(test_db, sample_user_data):
    """Тест обновления флага активности пользователя."""
    # Создаём активного пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"],
        active=True
    )
    
    # Деактивируем
    await update_user_active_flag(sample_user_data["tg_id"], False)
    user = await get_user_by_tg_id(sample_user_data["tg_id"])
    assert user["active_flag"] == 0
    
    # Активируем обратно
    await update_user_active_flag(sample_user_data["tg_id"], True)
    user = await get_user_by_tg_id(sample_user_data["tg_id"])
    assert user["active_flag"] == 1


@pytest.mark.asyncio
async def test_is_user_registered(test_db, sample_user_data):
    """Тест проверки регистрации пользователя."""
    # Пользователь не зарегистрирован
    assert await is_user_registered(sample_user_data["tg_id"]) is False
    
    # Создаём активного пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"],
        active=True
    )
    
    # Пользователь зарегистрирован и активен
    assert await is_user_registered(sample_user_data["tg_id"]) is True
    
    # Деактивируем
    await update_user_active_flag(sample_user_data["tg_id"], False)
    
    # Пользователь не активен
    assert await is_user_registered(sample_user_data["tg_id"]) is False


@pytest.mark.asyncio
async def test_is_user_exists(test_db, sample_user_data):
    """Тест проверки существования пользователя."""
    # Пользователь не существует
    assert await is_user_exists(sample_user_data["tg_id"]) is False
    
    # Создаём пользователя (даже неактивного)
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"],
        active=False
    )
    
    # Пользователь существует (даже если неактивен)
    assert await is_user_exists(sample_user_data["tg_id"]) is True


@pytest.mark.asyncio
async def test_is_user_admin(test_db, sample_user_data, sample_admin_data):
    """Тест проверки, является ли пользователь администратором."""
    # Создаём обычного пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role="employee"
    )
    
    # Создаём администратора
    await create_user(
        tg_id=sample_admin_data["tg_id"],
        username=sample_admin_data["username"],
        name=sample_admin_data["name"],
        role="admin"
    )
    
    # Проверяем
    assert await is_user_admin(sample_user_data["tg_id"]) is False
    assert await is_user_admin(sample_admin_data["tg_id"]) is True


@pytest.mark.asyncio
async def test_add_work_day(test_db, sample_user_data):
    """Тест добавления рабочего дня."""
    # Создаём пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Добавляем рабочий день
    today = date.today().isoformat()
    await add_work_day(sample_user_data["tg_id"], today, "office")
    
    # Проверяем
    work_day = await get_work_day(sample_user_data["tg_id"], today)
    assert work_day is not None
    assert work_day["status"] == "office"
    
    # Обновляем статус
    await add_work_day(sample_user_data["tg_id"], today, "remote")
    work_day = await get_work_day(sample_user_data["tg_id"], today)
    assert work_day["status"] == "remote"


@pytest.mark.asyncio
async def test_get_work_days(test_db, sample_user_data):
    """Тест получения рабочих дней за период."""
    # Создаём пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Добавляем несколько рабочих дней
    dates = ["2025-01-01", "2025-01-02", "2025-01-03"]
    for date_str in dates:
        await add_work_day(sample_user_data["tg_id"], date_str, "office")
    
    # Получаем рабочие дни за период
    work_days = await get_work_days(
        sample_user_data["tg_id"],
        "2025-01-01",
        "2025-01-03"
    )
    assert len(work_days) == 3
    
    # Получаем рабочие дни за меньший период
    work_days = await get_work_days(
        sample_user_data["tg_id"],
        "2025-01-01",
        "2025-01-02"
    )
    assert len(work_days) == 2


@pytest.mark.asyncio
async def test_add_vacation(test_db, sample_user_data):
    """Тест добавления отпуска."""
    # Создаём пользователя
    await create_user(
        tg_id=sample_user_data["tg_id"],
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Добавляем отпуск
    vacation_id = await add_vacation(
        tg_id=sample_user_data["tg_id"],
        start_date="2025-12-01",
        end_date="2025-12-10",
        vacation_type="vacation"
    )
    assert vacation_id is not None
    
    # Получаем отпуска
    vacations = await get_vacations(sample_user_data["tg_id"])
    assert len(vacations) == 1
    assert vacations[0]["start_date"] == "2025-12-01"
    assert vacations[0]["end_date"] == "2025-12-10"
    assert vacations[0]["type"] == "vacation"


@pytest.mark.asyncio
async def test_update_user_tg_id(test_db, sample_user_data):
    """Тест обновления tg_id пользователя."""
    # Создаём пользователя с временным отрицательным ID
    old_tg_id = -100
    await create_user(
        tg_id=old_tg_id,
        username=sample_user_data["username"],
        name=sample_user_data["name"],
        role=sample_user_data["role"]
    )
    
    # Обновляем tg_id
    new_tg_id = sample_user_data["tg_id"]
    success = await update_user_tg_id(old_tg_id, new_tg_id)
    assert success is True
    
    # Проверяем, что старый ID не существует
    old_user = await get_user_by_tg_id(old_tg_id)
    assert old_user is None
    
    # Проверяем, что новый ID существует
    new_user = await get_user_by_tg_id(new_tg_id)
    assert new_user is not None
    assert new_user["username"] == sample_user_data["username"]


@pytest.mark.asyncio
async def test_register_admin_if_needed(test_db):
    """Тест автоматической регистрации администратора."""
    # Мокаем DEFAULT_ADMINS в bot.config, так как функция импортирует его оттуда внутри себя
    # Используем patch для патчинга bot.config.DEFAULT_ADMINS
    test_admins = ["testadmin"]
    
    with patch('bot.config.DEFAULT_ADMINS', test_admins):
        # Регистрируем администратора
        success = await register_admin_if_needed(
            tg_id=888888888,
            username="testadmin",
            name="Test Admin"
        )
        assert success is True
        
        # Проверяем, что администратор создан
        user = await get_user_by_tg_id(888888888)
        assert user is not None
        assert user["role"] == "admin"
        assert user["username"] == "testadmin"
        
        # Пытаемся зарегистрировать не-админа
        success = await register_admin_if_needed(
            tg_id=777777777,
            username="notadmin",
            name="Not Admin"
        )
        assert success is False
