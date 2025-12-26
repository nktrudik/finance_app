"""
Настройка подключения к базе данных.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app import config

# Создаём движок БД
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Только для SQLite
)

# Сессия для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db():
    """
    Dependency для получения сессии БД в endpoint'ах.
    
    Использование:
        @app.post("/users")
        def create_user(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
