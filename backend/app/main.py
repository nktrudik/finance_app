"""
Financial RAG API - главный файл приложения.
"""
import os
print(f"!!! DEBUG: ПРОЦЕСС СТАРТАНУЛ. PORT={os.environ.get('PORT')}", flush=True)
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import config
from app.core.database import Base, engine, get_db
from app.core.logging_config import setup_logging
from app.core.models import User
from app.core.qdrant_client import create_collection, get_qdrant_client
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.schemas import (
    QueryRequest,
    QueryResponse,
    Token,
    UploadResponse,
    UserRegister,
    UserResponse,
)
from app.services.embedding_service import EmbeddingService
from app.services.indexing_service import IndexingService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

# ============= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =============

# RAG сервисы (инициализируются в lifespan)
qdrant_client = None
indexing_service = None
embedding_service = None


# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
setup_logging()
logger = logging.getLogger(__name__)


# ============= LIFESPAN EVENT =============


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Выполняется при запуске и остановке приложения.

    Код ДО yield - выполняется при старте (startup).
    Код ПОСЛЕ yield - выполняется при остановке (shutdown).
    """
    # ===== STARTUP =====
    logger.info("Financial RAG API запускается...")

    # Создание таблиц в БД
    Base.metadata.create_all(bind=engine)
    logger.info(f"База данных: {config.config.DATABASE_URL}")

    # Подключаемся к векторной БД
    logger.info("Подключение к Qdrant...")
    global qdrant_client
    qdrant_client = get_qdrant_client(config.config.QDRANT_URL)

    # Создание коллекции в Qdrant (если не существует)
    logger.info("Проверка коллекции в Qdrant...")
    create_collection(qdrant_client, config.config.QDRANT_COLLECTION_NAME)
    logger.info(f"Коллекция '{config.config.QDRANT_COLLECTION_NAME}' готова")

    logger.info("Загрузка embedding моделей...")
    global embedding_service
    embedding_service = EmbeddingService(cache_dir=config.config.MODELS_DIR)
    logger.info("Embedding модели загружены:")
    logger.info(f"  - Dense: {config.config.DENSE_MODEL_NAME}")
    logger.info(f"  - Sparse: {config.config.SPARSE_MODEL_NAME}")

    # Инициализация Indexing Service
    logger.info("Инициализация Indexing Service...")
    global indexing_service
    indexing_service = IndexingService(qdrant_client)
    logger.info("Indexing Service готов")

    # Проверка количества транзакций в Qdrant
    try:
        collection_info = qdrant_client.get_collection(config.config.QDRANT_COLLECTION_NAME)
        points_count = collection_info.points_count
        logger.info(f"Транзакций в Qdrant: {points_count}")
    except Exception as e:
        logger.warning(f"Не удалось получить статистику Qdrant: {e}")

    logger.info(f"Документация: http://{config.config.API_HOST}:{config.config.API_PORT}/docs")
    logger.info("API готов к работе!")

    yield  # Приложение работает

    # ===== SHUTDOWN =====
    logger.info("Остановка приложения...")

    # Очистка ресурсов
    if qdrant_client:
        logger.info("Закрытие соединения с Qdrant...")
        qdrant_client.close()

    logger.info("Приложение остановлено")


# ============= СОЗДАНИЕ ПРИЛОЖЕНИЯ =============

app = FastAPI(
    title="Financial RAG API",
    description="AI-powered personal finance assistant with RAG",
    version="1.0.0",
    lifespan=lifespan,
)


# ============= CORS =============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= HEALTH CHECK =============


@app.get("/", tags=["Health"])
async def root():
    """Проверка что API работает"""
    logger.debug("GET / вызван, используемая ручка: root, tags={['Health']}")
    return {
        "message": "Financial RAG API",
        "status": "ok",
        "version": "1.0.0",
        "docs": "/docs",
        "services": {
            "qdrant": qdrant_client is not None,
            "embedding": embedding_service is not None,
            "indexing": indexing_service is not None,
        },
    }


@app.get("/health", tags=["Служебное"])
async def health_check():
    """Детальная проверка здоровья сервисов"""

    health_status = {"status": "ok", "services": {}}

    # Проверка Qdrant
    try:
        if qdrant_client:
            collection_info = qdrant_client.get_collection(config.QDRANT_COLLECTION_NAME)
            health_status["services"]["qdrant"] = {
                "status": "ok",
                "points_count": collection_info.points_count,
            }
        else:
            health_status["services"]["qdrant"] = {"status": "not_initialized"}
    except Exception as e:
        health_status["services"]["qdrant"] = {"status": "error", "message": str(e)}
        health_status["status"] = "degraded"

    # Проверка Embedding Service
    health_status["services"]["embedding"] = {
        "status": "ok" if embedding_service else "not_initialized"
    }

    # Проверка Indexing Service
    health_status["services"]["indexing"] = {
        "status": "ok" if indexing_service else "not_initialized"
    }

    return health_status


# ============= AUTH ENDPOINTS =============


@app.post(
    "/api/v1/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    logger.info("🔄 Попытка регистрации: %s", user_data.username)

    # Проверка email
    if db.query(User).filter(User.email == user_data.email).first():
        logger.warning("⚠️ Email уже зарегистрирован: %s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже зарегистрирован"
        )

    # Проверка username
    if db.query(User).filter(User.username == user_data.username).first():
        logger.warning("⚠️ Username уже занят: %s", user_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username уже занят")

    # Создание пользователя
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Пользователь зарегистрирован: {new_user.username}")

    return new_user


@app.post("/api/v1/auth/login", response_model=Token, tags=["Authentication"])
async def login(credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Вход пользователя"""
    logger.info("🔄 Попытка входа: %s", credentials.username)

    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning("Неудачная попытка входа: %s", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль"
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info(f"Пользователь вошёл: {user.username}")

    return Token(access_token=access_token)


# ============= RAG ENDPOINTS =============


@app.post("/api/v1/upload", response_model=UploadResponse, tags=["Транзакции"])
async def upload_csv(
    file: UploadFile = File(...),
    replace: bool = Query(False, description="Заменить все существующие транзакции?"),
    current_user: User = Depends(get_current_user),
):
    """
    Docstring для upload_csv

    :param file: Принимаем csv файл и загружаем его
    :type file: UploadFile
    """
    logger.info(f"Пользователь {current_user.id} загружает CSV: {file.filename}")

    if not file.filename.endswith(".csv"):
        logger.error(f"Неверный формат файла: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Файл должен быть в формате CSV"
        )

    if not indexing_service:
        logger.error("Indexing Service не инициализирован")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис индексации не готов. Попробуйте позже.",
        )

    old_count = indexing_service.count_user_transactions(current_user.id)
    logger.info(f"Транзакций в Qdrant до загрузки: {old_count}")

    # Предупреждение если уже есть данные и replace=False
    if old_count > 0 and not replace:
        logger.info(
            f"ℹУ пользователя уже есть {old_count} транзакций. Будут добавлены новые (дубликаты перезапишутся)."
        )
    elif old_count > 0 and replace:
        logger.warning(f"REPLACE MODE: {old_count} существующих транзакций будут удалены!")

    temp_dir = config.TEMP_DIR
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"user_{current_user.id}_{file.filename}"

    try:
        with open(file=temp_path, mode="wb") as buffer:
            content = await file.read()
            buffer.write(content)
        file_size_kb = len(content) / 1024
        logger.info(f"CSV сохранён: {temp_path} ({file_size_kb:.1f} KB)")

        # Загружаем транзакции в Qdrant
        logger.info(f"Начинаем индексацию (replace={replace})...")

        loaded_count = indexing_service.load_from_csv(
            csv_path=str(temp_path),
            user_id=current_user.id,
            replace=replace,
        )

        # Получаем статистику ПОСЛЕ загрузки
        new_total = indexing_service.count_user_transactions(current_user.id)

        # Вычисляем реальные изменения
        if replace:
            # При replace: old_count удалены, loaded_count добавлены
            added_new = loaded_count
            updated_existing = 0
            deleted = old_count
        else:
            # При НЕ replace: часть могли быть дубликатами (перезаписаны)
            actually_added = new_total - old_count
            updated_existing = loaded_count - actually_added
            added_new = actually_added
            deleted = 0

        logger.info(f"   Загрузка завершена для user_id={current_user.id}")
        logger.info(f"   Обработано из CSV: {loaded_count}")
        logger.info(f"   Новых добавлено: {added_new}")
        logger.info(f"   Перезаписано (дубликаты): {updated_existing}")
        logger.info(f"   Итого в Qdrant: {new_total}")

        # 9. Формируем детальный ответ
        return {
            "status": "success",
            "message": f"CSV '{file.filename}' успешно обработан",
            "user": {"id": current_user.id, "email": current_user.email},
            "file": {"name": file.filename, "size_kb": round(file_size_kb, 2)},
            "statistics": {
                "processed_from_csv": loaded_count,  # Сколько было в CSV
                "before_upload": old_count,  # Было в Qdrant до загрузки
                "after_upload": new_total,  # Стало в Qdrant после загрузки
                "added_new": added_new,  # Добавлено новых
                "updated_duplicates": updated_existing,  # Перезаписано дубликатов
                "deleted": deleted,  # Удалено (если replace=true)
                "mode": "replace" if replace else "append",
            },
            "next_steps": {
                "view_transactions": "/api/v1/transactions",
                "chat": "/api/v1/chat",
                "stats": "/api/v1/transactions/stats",
            },
        }

    except FileNotFoundError:
        logger.error(f" Файл не найден: {temp_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CSV файл не найден на сервере"
        )

    except ValueError as e:
        # Ошибки парсинга CSV (неверный формат)
        logger.error(f"Ошибка парсинга CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка формата CSV: {str(e)}. Проверьте структуру файла.",
        )

    except Exception as e:
        # Остальные ошибки
        logger.error(f"Ошибка при обработке CSV: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обработки файла: {str(e)}",
        )

    finally:
        # Удаляем временный файл
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Временный файл удалён: {temp_path}")


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG"])
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Задать вопрос финансовому ассистенту (RAG).
    
    Args:
        request: {"query": "Сколько на кафе?"}
        current_user: Авторизованный пользователь (из JWT)
    
    Returns:
        QueryResponse: {"answer": "...", "transactions": [...]}
    """
    
    logger.info(f"RAG запрос от {current_user.username}: '{request.query}'")
    
    try:
        # Инициализируем RAG сервисы (из DI контейнера или глобально)
        rag_service = RAGService(
            qdrant=get_qdrant_client(),
            embedder=EmbeddingService(),
            llm=LLMService()
        )
        
        # Вызываем RAG
        result = await rag_service.ask(
            query=request.query,
            user_id=current_user.id
        )
            
        logger.info(f"RAG ответ отправлен пользователю {current_user.username}")
        return QueryResponse(
            query=result['query'],
            answer=result['answer'],
            sources=result["transactions"], 
            found_count=result["found_count"]
        )
    
    except Exception as e:
        logger.error(f"RAG ошибка: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")


