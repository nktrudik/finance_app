# backend/app/config.py
"""
Централизованная конфигурация бэкенда приложения.

Все переменные загружаются из .env файла.
Порядок приоритета:
1. .env файл (если существует)
2. Значения по умолчанию в этом файле
3. Переменные окружения системы
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============= ИНИЦИАЛИЗАЦИЯ ОКРУЖЕНИЯ =============
# Загружаем переменные из .env файла
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=False)

# ============= БАЗОВЫЕ ПУТИ =============
# Корневая директория: backend/
BASE_DIR = Path(__file__).parent.parent

# Директория для данных (БД, Qdrant, etc.)
DATA_DIR = BASE_DIR / "data"

# Директория для моделей (HuggingFace embeddings)
MODELS_DIR = BASE_DIR / "models"

# Директория для логов
LOGS_DIR = BASE_DIR / "logs"

# Директория для временных файлов (uploads, etc.)
TEMP_DIR = BASE_DIR / "temp"

# Автоматически создаём все необходимые директории
for directory in [DATA_DIR, MODELS_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============= ОКРУЖЕНИЕ =============
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = ENVIRONMENT == "development"

# ============= ЛОГИРОВАНИЕ =============
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = LOGS_DIR / "app.log"

# ============= DATABASE (SQLite) =============
DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

# ============= QDRANT VECTOR DATABASE =============
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION_NAME = "financial_transactions"

# ============= EMBEDDINGS =============
EMBEDDING_CACHE_DIR = str(MODELS_DIR / "embeddings")
BATCH_SIZE = 32

# Модели для embeddings (НЕ менять!) 
DENSE_MODEL_NAME = "BAAI/bge-large-en-v1.5"
SPARSE_MODEL_NAME = "Qdrant/bm25"

# ============= БЕЗОПАСНОСТЬ (JWT) =============
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "your-secret-key-change-in-production-use-python-secrets-to-generate"
)

# Проверка SECRET_KEY в production
if IS_PRODUCTION and SECRET_KEY.startswith("your-secret-key"):
    raise ValueError(
        "SECRET_KEY не установлен! "
        "Установите переменную окружения SECRET_KEY. "
        "Сгенерируйте с: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

ALGORITHM = "HS256"  # JWT алгоритм (НЕ менять!)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

# ============= API =============
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ============= LLM (ОПЦИОНАЛЬНО) =============
# Эти переменные нужны только если используется LLM интеграция
# LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")  # openrouter, ollama, openai
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")

# ============= DEBUG INFO =============
if IS_DEVELOPMENT:
    # Вывести конфиг при запуске в development режиме (без secrets)
    print(f"""
    ╔════════════════════════════════════════╗
    ║   FINANCE APP RAG - Конфигурация       ║
    ╚════════════════════════════════════════╝
    Environment: {ENVIRONMENT}
    Database: {DATABASE_URL}
    Qdrant: {QDRANT_URL}
    Data Dir: {DATA_DIR}
    Models Dir: {MODELS_DIR}
    Logs Dir: {LOGS_DIR}
    """)
