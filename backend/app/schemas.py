"""
Pydantic модели для query endpoint.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class UploadStatistics(BaseModel):
    """Статистика загрузки"""

    processed_from_csv: int
    before_upload: int
    after_upload: int
    added_new: int
    updated_duplicates: int
    deleted: int
    mode: str


class QueryRequest(BaseModel):
    """Запрос от пользователя"""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Вопрос о финансах",
        examples=["Сколько я тратил за последний месяц на супермаркеты?"],
    )


class SourceDocument(BaseModel):
    """Исходная транзакция из RAG"""
    date: str
    amount: float
    category: str
    description: str
    score: Optional[float] = None 


class QueryResponse(BaseModel):
    """Ответ на вопрос пользователя"""
    query: str
    answer: str
    sources: List[SourceDocument] = []
    found_count: int = 0


class UploadResponse(BaseModel):
    """Ответ после загрузки CSV"""

    status: str
    message: str
    user: Dict[str, Any]
    file: Dict[str, Any]
    statistics: UploadStatistics
    next_steps: Dict[str, str]


class UserRegister(BaseModel):
    """
    Схема для регистрации пользователя.

    Что iOS отправляет при регистрации:
    POST /api/v1/auth/register
    {
        "email": "user@example.com",
        "username": "testuser",
        "password": "password123"
    }
    """

    email: EmailStr = Field(..., description="Email пользователя")
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    password: str = Field(
        ..., min_length=8, max_length=100, description="Пароль (минимум 8 символов)"
    )

    # class UserLogin(BaseModel):
    """
    Схема для входа пользователя.
    
    Что iOS отправляет при логине:
    POST /api/v1/auth/login
    {
        "email": "testuser",
        "password": "password123"
    }
    """
    # username: str = Field(..., description="Имя пользователя")
    # password: str = Field(..., description="Пароль")


class UserResponse(BaseModel):
    """
    Схема ответа с данными пользователя.

    Что backend возвращает iOS после регистрации:
    {
        "id": 1,
        "email": "user@example.com",
        "username": "testuser",
        "created_at": "2025-12-27T13:45:00"
    }
    """

    id: int
    email: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True  # Позволяет создавать из SQLAlchemy объекта User


class Token(BaseModel):
    """
    Схема JWT токена.

    Что backend возвращает iOS после успешного логина:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }

    iOS сохраняет этот токен и отправляет в заголовках:
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """

    access_token: str = Field(..., description="JWT токен")
    token_type: str = Field(default="bearer", description="Тип токена (всегда bearer)")
