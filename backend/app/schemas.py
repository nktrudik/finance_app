"""
Pydantic модели для query endpoint.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


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
    documents_processed: int
    date_range: Optional[Dict[str, str]] = None  # {"from": "2024-01-01", "to": "2024-12-31"}