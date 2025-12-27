"""
Financial RAG API - главный файл приложения.
"""
import shutil, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
from app import config
from app.schemas import (
    QueryRequest, 
    QueryResponse, 
    UploadResponse,
    UserRegister,
    UserLogin,
    UserResponse,
    Token
)
from app.core.database import engine, Base, get_db
from app.core.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.logging_config import setup_logging

# ============= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =============

# RAG сервисы (инициализируются в lifespan)
vector_service = None
llm_service = None
qa_chain = None


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
    logger.info(f"База данных: {config.DATABASE_URL}")
    
    # TODO: Инициализация RAG сервисов (после их создания)
    # global vector_service, llm_service
    # 
    # print("📦 Загрузка embeddings модели (e5-large)...")
    # vector_service = VectorStoreService()
    # print("✅ Embeddings готовы")
    # 
    # print("🤖 Загрузка LLM (VLLM)...")
    # llm_service = LLMService()
    # print("✅ LLM готов")
    
    logger.info(f"Документация: http://{config.API_HOST}:{config.API_PORT}/docs")
    logger.info("API готов к работе!")
    
    yield  # Приложение работает
    
    # ===== SHUTDOWN =====
    logger.info("Остановка приложения...")
    
    # TODO: Очистка ресурсов (если нужно)
    # if vector_service:
    #     print("🧹 Очистка векторного хранилища...")
    # if llm_service:
    #     print("🧹 Выгрузка LLM...")
    
    logger.info("Приложение остановлено")


# ============= СОЗДАНИЕ ПРИЛОЖЕНИЯ =============

app = FastAPI(
    title="Financial RAG API",
    description="AI-powered personal finance assistant with RAG",
    version="1.0.0",
    lifespan=lifespan 
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
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health():
    """Проверка состояния всех сервисов"""
    logger.debug("Health check вызван")
    return {
        "status": "ok",
        "services": {
            "database": True,
            "vector_store": vector_service is not None,
            "llm": llm_service is not None,
            "data_loaded": qa_chain is not None
        }
    }


# ============= AUTH ENDPOINTS =============

@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    logger.info("🔄 Попытка регистрации: %s", user_data.username)
    
    # Проверка email
    if db.query(User).filter(User.email == user_data.email).first():
        logger.warning("⚠️ Email уже зарегистрирован: %s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )
    
    # Проверка username
    if db.query(User).filter(User.username == user_data.username).first():
        logger.warning("⚠️ Username уже занят: %s", user_data.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username уже занят"
        )
    
    # Создание пользователя
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Пользователь зарегистрирован: {new_user.username}")
    
    return new_user


@app.post("/api/v1/auth/login", response_model=Token, tags=["Authentication"])
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Вход пользователя"""
    logger.info("🔄 Попытка входа: %s", credentials.username)

    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning("⚠️ Неудачная попытка входа: %s", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"Пользователь вошёл: {user.username}")
    
    return Token(access_token=access_token)


# ============= RAG ENDPOINTS =============

@app.post("/api/v1/upload", response_model=UploadResponse, tags=["RAG"])
async def upload_csv(file: UploadFile = File(...)):
    """Загрузка CSV с транзакциями"""
    logger.info("📄 Загрузка CSV: %s", file.filename)

    global qa_chain
    
    if not file.filename.endswith('.csv'):
        logger.warning("⚠️ Неверный формат файла: %s", file.filename)
        raise HTTPException(status_code=400, detail="Нужен CSV файл")
    
    temp_dir = Path("./temp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"upload_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"CSV загружен: {file.filename}")
        
        # TODO: После создания сервисов
        # from app.services.csv_parser import CSVParser
        # documents = CSVParser.parse_transactions(str(temp_path))
        # vectorstore = vector_service.create_vectorstore(documents)
        # qa_chain = llm_service.create_qa_chain(vectorstore)
        
        return UploadResponse(
            status="success",
            message=f"CSV {file.filename} загружен (заглушка)",
            documents_processed=0,
            date_range=None
        )
    
    except Exception as e:
        logger.error("Ошибка при обработке CSV: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_path.exists():
            temp_path.unlink()
            logger.debug("Временный файл удалён: %s", temp_path)



@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG"])
async def query(request: QueryRequest):
    """Задать вопрос финансовому ассистенту"""
    logger.info("Вопрос: %s", request.question)
    
    if qa_chain is None:
        logger.warning("Попытка запроса без загруженных данных")
        raise HTTPException(
            status_code=400,
            detail="Сначала загрузите CSV через /api/v1/upload"
        )
    
    try:
        logger.info("Ответ сгенерирован")
        
        # TODO: После создания LLMService
        # result = llm_service.answer(qa_chain, request.question)
        # return QueryResponse(
        #     question=request.question,
        #     answer=result['answer'],
        #     sources=[SourceDocument(**s) for s in result['sources']]
        # )
        
        return QueryResponse(
            question=request.question,
            answer="Заглушка. RAG не подключен.",
            sources=[]
        )
    
    except Exception as e:
        logger.error("Ошибка при обработке запроса: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
