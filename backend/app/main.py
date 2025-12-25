from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import shutil
import os
from pathlib import Path
from app import config
# ✅ Импортируем модели из schemas
from app.schemas.query import QueryRequest, QueryResponse
from app.schemas.upload import UploadResponse


# ============= СОЗДАНИЕ FASTAPI APP =============
app = FastAPI(
    title = "Financial RAG API",
    description = "AI personal finance assistant"
)


# ============= НАСТРОЙКА ДОСТУПА ДЛЯ ДРУГИХ СЕРВИСОВ ДЛЯ ДОСТУПА К НАШЕМУ АПИ =============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Кому разрешаем доступ
    allow_credentials=True,   # Разрешаем ли куки/токены
    allow_methods=["*"],      # Какие HTTP-методы
    allow_headers=["*"],      # Какие заголовки
)


# ============= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ СЕРВИСОВ =============

# Инициализируем при старте приложения (ленивая загрузка)
vector_service = None  # TODO: VectorStoreService()
llm_service = None     # TODO: LLMService()
qa_chain = None        # TODO: RAG цепочка после загрузки CSV




