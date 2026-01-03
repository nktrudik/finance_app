"""
Pydantic модели для query endpoint.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

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
    question: str = Field(
        ..., 
        min_length=3, 
        max_length=500,
        description="Вопрос о финансах",
        examples=["Сколько я тратил за последнюю неделю на кафешки?"]
    )


class SourceDocument(BaseModel):
    """Исходная транзакция из RAG"""
    date: str
    amount: float
    category: str
    description: str
    merchant: Optional[str] = None


class QueryResponse(BaseModel):
    """Ответ на вопрос пользователя"""
    question: str
    answer: str
    sources: List[SourceDocument]
    processing_time: Optional[float] = None


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
    password: str = Field(..., min_length=8, max_length=100, description="Пароль (минимум 8 символов)")


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
    
    ⚠️ ВАЖНО: НЕ возвращаем пароль! (даже хешированный)
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