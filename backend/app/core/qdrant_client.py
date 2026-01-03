from qdrant_client import QdrantClient, models
from app.config import QDRANT_URL, QDRANT_COLLECTION_NAME
import logging

logger = logging.getLogger(__name__)


def get_qdrant_client(url: str = QDRANT_URL) -> QdrantClient:
    """
    Docstring для get_qdrant_client
    
    :param url: Получаем ссылку на клиента
    :type url: str
    :return: Возвращаем самого клиента Qdrant
    :rtype: Any    
    """

    try:
        logger.info(f"Подключение к Qdrant: {url}")
        client = QdrantClient(url=url)
        
        # Проверка подключения
        client.get_collections()
        logger.info("Успешное подключение к Qdrant")
        
        return client
    except Exception as e:
        logger.error(f"Ошибка подключения к Qdrant: {e}")
        raise ConnectionError(f"Не удалось подключиться к Qdrant ({url}): {e}")
    

def create_collection(client: QdrantClient, collection_name: str = QDRANT_COLLECTION_NAME):
    """
    Docstring для create_collection
    
    :param client: Принимает Qdrant клиента
    :type client: QdrantClient
    :param collection_name: Принимает имя коллекции и создает коллекцию
    :type collection_name: str
    """
    try:
        # Проверяем существование коллекции
        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            logger.info(f"Коллекция '{collection_name}' уже существует")
            return 
        
        logger.info(f"Создаём коллекцию '{collection_name}'...")

        # Создаём коллекцию с поддержкой гибридного поиска (Sparse + Dense вектора)
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF
                )
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при создании коллекции: {e}")
        raise

    logger.info("Создаём payload индексы для быстрой фильтрации...")

    # Индексы для ускорения фильтрации
    indexes = [
        ("user_id", models.PayloadSchemaType.INTEGER),
        ("year", models.PayloadSchemaType.INTEGER),
        ("month", models.PayloadSchemaType.INTEGER),
        ("quarter", models.PayloadSchemaType.INTEGER),
        ("category", models.PayloadSchemaType.KEYWORD),
        ("is_expense", models.PayloadSchemaType.BOOL),
    ]

    for field_name, field_schema in indexes:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=field_schema
        )
        logger.info(f"Индекс для '{field_name}' создан")
    
    logger.info(f"Коллекция '{collection_name}' готова!")
