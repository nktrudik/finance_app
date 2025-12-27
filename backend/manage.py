"""
Управление проектом - CLI команды.

Использование:
    python manage.py check-db
    python manage.py reset-db
    python manage.py seed-db
"""

import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, engine
from app.core.models import User
from app.core.security import hash_password
from app import config


def check_db():
    """Проверка базы данных - показать всех пользователей"""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        print(f"\n📊 Всего пользователей в БД: {len(users)}\n")
        print("=" * 60)
        
        if not users:
            print("⚠️  База данных пустая.")
            print("   Зарегистрируйте пользователя через /api/v1/auth/register\n")
            return
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Username: {user.username}")
            print(f"Пароль (хеш): {user.hashed_password[:60]}...")
            print(f"Создан: {user.created_at}")
            print("-" * 60)
        
    finally:
        db.close()


def reset_db():
    """Сброс базы данных (удалить все таблицы и создать заново)"""
    print("⚠️  ВНИМАНИЕ: Это удалит все данные из БД!")
    confirm = input("Продолжить? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("❌ Отменено")
        return
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ База данных сброшена\n")


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
        # Проверяем что пользователь ещё не существует
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"⚠️  Пользователь {user_data['username']} уже существует")
            continue
        
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=hash_password(user_data["password"])
        )
        db.add(user)
        print(f"✅ Создан пользователь: {user_data['username']}")
    
    db.commit()
    db.close()
    print(f"\n✅ Тестовые данные добавлены\n")


def create_tables():
    """Создать таблицы в БД (если их нет)"""
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы\n")


def main():
    """Главная функция - обработка команд"""
    parser = argparse.ArgumentParser(
        description="Управление проектом Financial RAG API"
    )
    
    parser.add_argument(
        "command",
        choices=["check-db", "reset-db", "seed-db", "create-tables"],
        help="Команда для выполнения"
    )
    
    args = parser.parse_args()
    
    # Выполнение команды
    commands = {
        "check-db": check_db,
        "reset-db": reset_db,
        "seed-db": seed_db,
        "create-tables": create_tables,
    }
    
    commands[args.command]()


if __name__ == "__main__":
    main()

