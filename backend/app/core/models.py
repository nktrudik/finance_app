# Класс пользователя, данные после регистрации

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class User(Base):
    """SQLAlchemy модель - структура таблицы в БД"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # В БД: INTEGER PRIMARY KEY
    email = Column(String, unique=True)  # В БД: VARCHAR UNIQUE
    username = Column(String, unique=True)  # В БД: VARCHAR UNIQUE
    hashed_password = Column(String)  # В БД: VARCHAR
    created_at = Column(DateTime, default=datetime.utcnow)  # В БД: TIMESTAMP
