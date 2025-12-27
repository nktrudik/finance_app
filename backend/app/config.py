"""
Конфигурация бэкенда.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Корневая директория проекта и базовые настройки
BASE_DIR = Path(__file__).parent.parent  # backend/
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


# ============= DATA =============
DATA_DIR = BASE_DIR / "data"

DATABASE_URL = f"sqlite:///{str(DATA_DIR/ 'app.db')}"
QDRANT_PATH = DATA_DIR / "qdrant_storage" 
QDRANT_COLLECTION_NAME = "financial_transactions"


# ============= БЕЗОПАСНОСТЬ =============
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
ALGORITHM = os.getenv("ALGORITHM")
SECRET_KEY = os.getenv("SECRET_KEY")


# ============= API =============
API_HOST = os.getenv("API_HOST")
API_PORT = int(os.getenv("API_PORT"))

# ============= LLM НАСТРОЙКИ =============
LLM_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.7

# ============= EMBEDDINGS =============
EMBEDDING_MODEL_NAME = "intfloat/e5-large-v2"
EMBEDDING_DEVICE = "cpu"  # Или "cuda" если на GPU


# ============= RAG ПАРАМЕТРЫ =============
RAG_TOP_K = 5  # Сколько транзакций брать из Qdrant
RAG_SCORE_THRESHOLD = 0.5  # Минимальная релевантность