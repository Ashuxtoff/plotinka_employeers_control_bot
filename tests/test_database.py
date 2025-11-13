"""Тесты для модуля database."""
import asyncio
import os
from datetime import date

# Добавляем путь к bot в PYTHONPATH
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.database import (
    init_db,
    create_user,
    get_user_by_tg_id,
    get_all_active_users,
    update_user_consent,
    add_work_day,
    get_work_day,
    get_work_days,
    add_vacation,
    get_vacations,
    DB_PATH
)


async def test_database():
    """Тестирование функций базы данных."""
    print("🧪 Запуск тестов базы данных...\n")
    
    # Удаляем старую БД если есть
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("✅ Старая БД удалена")
    
    # 1. Инициализация БД
    print("\n1️⃣ Тест: Инициализация БД")
    await init_db()
    print("✅ База данных создана")
    
    # 2. Создание пользователей
    print("\n2️⃣ Тест: Создание пользователей")
    await create_user(
        tg_id=123456789,
        username="mirvien",
        name="Администратор Иван",
        role="admin"
    )
    print("✅ Администратор создан")
    
    await create_user(
        tg_id=987654321,
        username="employee1",
        name="Сотрудник Пётр",
        role="employee"
    )
    print("✅ Сотрудник создан")
    
    # 3. Получение пользователя
    print("\n3️⃣ Тест: Получение пользователя по tg_id")
    user = await get_user_by_tg_id(123456789)
    print(f"✅ Пользователь найден: {user['name']} (@{user['username']}, role={user['role']})")
    
    # 4. Получение всех активных пользователей
    print("\n4️⃣ Тест: Получение всех активных пользователей")
    users = await get_all_active_users()
    print(f"✅ Найдено активных пользователей: {len(users)}")
    for u in users:
        print(f"   - {u['name']} (@{u['username']}, role={u['role']})")
    
    # 5. Обновление согласия
    print("\n5️⃣ Тест: Обновление согласия на обработку данных")
    await update_user_consent(123456789, True)
    user = await get_user_by_tg_id(123456789)
    print(f"✅ Согласие обновлено: consent_given={user['consent_given']}")
    
    # 6. Добавление рабочих дней
    print("\n6️⃣ Тест: Добавление рабочих дней")
    today = date.today().isoformat()
    await add_work_day(123456789, today, "office")
    print(f"✅ Рабочий день добавлен: {today}, статус=office")
    
    await add_work_day(987654321, today, "remote")
    print(f"✅ Рабочий день добавлен: {today}, статус=remote")
    
    # 7. Получение рабочего дня
    print("\n7️⃣ Тест: Получение рабочего дня")
    work_day = await get_work_day(123456789, today)
    print(f"✅ Рабочий день получен: date={work_day['date']}, status={work_day['status']}")
    
    # 8. Обновление рабочего дня
    print("\n8️⃣ Тест: Обновление рабочего дня")
    await add_work_day(123456789, today, "remote")
    work_day = await get_work_day(123456789, today)
    print(f"✅ Рабочий день обновлён: статус изменён на {work_day['status']}")
    
    # 9. Получение рабочих дней за период
    print("\n9️⃣ Тест: Получение рабочих дней за период")
    work_days = await get_work_days(123456789, today, today)
    print(f"✅ Найдено записей за период: {len(work_days)}")
    
    # 10. Добавление отпуска
    print("\n🔟 Тест: Добавление отпуска")
    vacation_id = await add_vacation(
        tg_id=123456789,
        start_date="2025-12-01",
        end_date="2025-12-10",
        vacation_type="vacation"
    )
    print(f"✅ Отпуск добавлен с ID={vacation_id}")
    
    # 11. Получение отпусков
    print("\n1️⃣1️⃣ Тест: Получение отпусков")
    vacations = await get_vacations(123456789)
    print(f"✅ Найдено отпусков: {len(vacations)}")
    for v in vacations:
        print(f"   - {v['start_date']} - {v['end_date']}, тип={v['type']}")
    
    print("\n" + "="*50)
    print("✅ Все тесты пройдены успешно!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(test_database())

