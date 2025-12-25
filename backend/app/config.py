"""
Конфигурация бэкенда.
"""

from pathlib import Path

# Корневая директория проекта
BASE_DIR = Path(__file__).parent.parent  # backend/

# ============= LLM НАСТРОЙКИ =============
LLM_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.7

# ============= EMBEDDINGS =============
EMBEDDING_MODEL_NAME = "intfloat/e5-large-v2"
EMBEDDING_DEVICE = "cpu"  # Или "cuda" если на GPU

# ============= QDRANT =============
QDRANT_PATH = BASE_DIR / "qdrant_storage"  # backend/qdrant_storage
QDRANT_COLLECTION_NAME = "financial_transactions"

# ============= RAG ПАРАМЕТРЫ =============
RAG_TOP_K = 5  # Сколько транзакций брать из Qdrant
RAG_SCORE_THRESHOLD = 0.5  # Минимальная релевантность

# ============= API =============
API_HOST = "0.0.0.0"
API_PORT = 8000
