"""
Конфигурация бэкенда.
"""

from pathlib import Path

# Корневая директория проекта
BASE_DIR = Path(__file__).parent.parent  # backend/


# ============= DATA =============
DATA_DIR = BASE_DIR / "data"

DATABASE_URL = f"sqlite:///{str(DATA_DIR/ 'app.db')}"
QDRANT_PATH = DATA_DIR / "qdrant_storage" 
QDRANT_COLLECTION_NAME = "financial_transactions"


# ============= API =============
API_HOST = "0.0.0.0"
API_PORT = 8000

ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7
ALGORITHM = "HS256"
SECRET_KEY = "XoTOD9ZM4wrDg57-yrTJ06meUSZErw9-Pc67ZDNk2Jo"


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