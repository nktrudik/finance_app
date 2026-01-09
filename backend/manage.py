"""
Управление проектом - CLI команды.

Использование:
    python manage.py check-db
    python manage.py reset-db
    python manage.py seed-db
    python manage.py delete-user <user_id>
"""

import argparse

from sqlalchemy.orm import sessionmaker

from app.config import QDRANT_URL
from app.core.database import Base, engine
from app.core.models import User
from app.core.qdrant_client import get_qdrant_client
from app.core.security import hash_password
from app.services.indexing_service import IndexingService


def check_qdrant():
    """Проверить количество транзакций в Qdrant для всех пользователей"""

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        users = db.query(User).all()

        if not users:
            print("В базе нет пользователей")
            return

        # Подключаемся к Qdrant
        client = get_qdrant_client(QDRANT_URL)
        indexing_service = IndexingService(client)

        print("\nСтатистика транзакций в Qdrant:\n")
        print("=" * 60)

        total_transactions = 0

        for user in users:
            count = indexing_service.count_user_transactions(user.id)
            total_transactions += count

            print(f"User ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Транзакций в Qdrant: {count}")
            print("-" * 60)

        print(f"\nВсего транзакций: {total_transactions}\n")

    except Exception as e:
        print(f"Ошибка Qdrant: {e}")
        raise

    finally:
        db.close()


def check_db():
    """Проверка базы данных - показать всех пользователей"""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        users = db.query(User).all()

        print(f"Всего пользователей в БД: {len(users)}\n")
        print("=" * 60)

        if not users:
            print("База данных пустая.")
            return

        # Подключаемся к Qdrant для подсчёта транзакций
        qdrant_client = get_qdrant_client(QDRANT_URL)
        indexing_service = IndexingService(qdrant_client)

        for user in users:
            # Считаем транзакции в Qdrant
            tx_count = indexing_service.count_user_transactions(user.id)

            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Username: {user.username}")
            print(f"Транзакций в Qdrant: {tx_count}")  # ← Показываем!
            print(f"Создан: {user.created_at}")
            print("-" * 60)

    finally:
        db.close()


def reset_db():
    """Сброс базы данных (удалить все таблицы и создать заново)"""
    print("ВНИМАНИЕ: Это удалит все данные из БД!")
    confirm = input("Продолжить? (yes/no): ")

    if confirm.lower() != "yes":
        print("Отменено")
        return

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("База данных сброшена\n")


def seed_db():
    """Заполнить БД тестовыми пользователями"""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    test_users = [
        {"email": "user1@test.com", "username": "user1", "password": "password123"},
        {"email": "user2@test.com", "username": "user2", "password": "password123"},
        {"email": "admin@test.com", "username": "admin", "password": "admin12345"},
    ]

    for user_data in test_users:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"⚠️  Пользователь {user_data['username']} уже существует")
            continue

        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=hash_password(user_data["password"]),
        )
        db.add(user)
        print(f"Создан пользователь: {user_data['username']}")

    db.commit()
    db.close()
    print(f"\nТестовые данные добавлены\n")


def delete_user(user_id: int):
    """
    Удалить пользователя из SQLite + его транзакции из Qdrant.

    Args:
        user_id: ID пользователя для удаления
    """
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 1. Ищем пользователя в SQLite
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            print(f"Пользователь с ID={user_id} не найден")
            return

        print(f"\n👤 Найден пользователь:")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")

        # 2. Считаем транзакции в Qdrant
        qdrant_client = get_qdrant_client(QDRANT_URL)
        indexing_service = IndexingService(qdrant_client)
        tx_count = indexing_service.count_user_transactions(user_id)

        print(f"   Транзакций в Qdrant: {tx_count}")

        # 3. Подтверждение
        print(f"\nБудет удалено:")
        print(f"   - Пользователь из SQLite")
        print(f"   - {tx_count} транзакций из Qdrant")

        confirm = input("\nПродолжить? (yes/no): ")

        if confirm.lower() != "yes":
            print("Отменено")
            return

        # 4. Удаляем из SQLite
        db.delete(user)
        db.commit()
        print("Пользователь удалён из SQLite")

        # 5. Удаляем транзакции из Qdrant
        if tx_count > 0:
            success = indexing_service.delete_user_transactions(user_id)
            if success:
                print(f"Удалено {tx_count} транзакций из Qdrant")
            else:
                print("Ошибка удаления из Qdrant")

        print(f"\nПользователь {user.username} полностью удалён!\n")

    finally:
        db.close()


def create_tables():
    """Создать таблицы в БД (если их нет)"""
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы\n")


def main():
    """Главная функция - обработка команд"""
    parser = argparse.ArgumentParser(description="Управление проектом Financial RAG API")

    parser.add_argument(
        "command",
        choices=["check-db", "reset-db", "seed-db", "create-tables", "delete-user"],
        help="Команда для выполнения",
    )

    parser.add_argument(
        "user_id",
        type=int,
        nargs="?",  # Опциональный аргумент
        help="ID пользователя (для delete-user)",
    )

    args = parser.parse_args()

    # Выполнение команды
    if args.command == "delete-user":
        if not args.user_id:
            print("Ошибка: укажите user_id")
            print("Использование: python manage.py delete-user <user_id>")
            return
        delete_user(args.user_id)
    else:
        commands = {
            "check-db": check_db,
            "check-qdrant": check_qdrant,
            "reset-db": reset_db,
            "seed-db": seed_db,
            "create-tables": create_tables,
            "delete-user": delete_user,
        }
        commands[args.command]()


if __name__ == "__main__":
    main()
