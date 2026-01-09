# backend/app/services/indexing_service.py
import hashlib
import logging
import uuid
from datetime import datetime

from qdrant_client import QdrantClient, models

from app.config import BATCH_SIZE, MODELS_DIR, QDRANT_COLLECTION_NAME
from app.services.embedding_service import EmbeddingService
from app.utils.csv_parser import format_transaction_text, parse_transactions_csv

logger = logging.getLogger(__name__)


class IndexingService:
    """Сервис для индексации транзакций в Qdrant"""

    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant = qdrant_client
        self.embedder = EmbeddingService(cache_dir=MODELS_DIR, batch_size=BATCH_SIZE)
        self.collection_name = QDRANT_COLLECTION_NAME

    def delete_user_transactions(self, user_id: int) -> bool:
        """
        Docstring для delete_user_transactions

        :param user_id: Уникальный ID пользователя
        :type user_id: int
        :return: Удаляет все транзакции пользователя из Qdrant
        :rtype: bool
        """
        logger.info(f"Удаление транзакций для user_id={user_id}")

        try:
            result = self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="user_id", match=models.MatchValue(value=user_id)
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Транзакции удалены из Qdrant")
            return True

        except Exception as e:
            logger.error(f"Ошибка удаления из Qdrant: {e}")
            return False

    def _generate_transaction_id(self, transaction: dict, user_id: int) -> str:
        """
        Docstring для generate_transaction_id

        :param transaction: Одна транзакция
        :type transaction: dict
        :param user_id: Уникальный ID юзера
        :type user_id: int
        :return: Детерминированный ID для траназакции. Одинаковые транзакции = одинаковые кэш.
        :rtype: str
        """
        # Ключевые поля для уникальности
        unique_string = (
            f"{user_id}|"
            f"{transaction['date']}|"
            f"{transaction['amount']}|"
            f"{transaction['category']}|"
            f"{transaction['description']}"
        )

        # SHA256 хеш
        hash_bytes = hashlib.sha256(unique_string.encode()).digest()
        transaction_uuid = str(uuid.UUID(bytes=hash_bytes[:16]))

        return transaction_uuid

    def load_from_csv(self, csv_path: str, user_id: int, replace: bool = False) -> int:
        """
        Docstring для load_from_csv

        :param csv_path: Наш csv файл
        :type csv_path: str
        :param user_id: Уникальный пользователь (его id)
        :type user_id: int
        :param replace: Хотим ли мы заменить нашего юзера
        :type replace: bool
        :return: Количество загруженных транзакций
        :rtype: int
        """
        try:
            logger.info(f"Загрузка транзакций из {csv_path} для user_id={user_id}")

            if replace:
                logger.info("Удаляем старые транзакции...")
                self.delete_user_transactions(user_id)

            try:
                transactions = parse_transactions_csv(csv_path)
                logger.info(f"Распарсено {len(transactions)} транзакций")

            except:
                logger.error(f"Модуль csv_parser не сработал")
                return 0

            if not transactions:
                logger.warning("Нет транзакций для загрузки!")
                return 0

            texts = [format_transaction_text(t) for t in transactions]
            dense_vectors, sparse_vectors = self.embedder.embed_batch(texts=texts)

            points = []

            for idx, transaction in enumerate(transactions):

                date_obj = datetime.fromisoformat(transaction["date"])

                # Payload = метаданные транзакции
                payload = {
                    # Основные поля
                    "date": transaction["date"],
                    "amount": transaction["amount"],
                    "category": transaction["category"],
                    "description": transaction["description"],
                    "mcc": transaction["mcc"],
                    "cashback": transaction["cashback"],
                    "is_expense": transaction["is_expense"],
                    # Фильтры (для быстрого поиска)
                    "user_id": user_id,
                    "year": date_obj.year,
                    "month": date_obj.month,
                    "quarter": (date_obj.month - 1) // 3 + 1,
                    "day_of_week": date_obj.weekday(),
                }

                transaction_id = self._generate_transaction_id(transaction, user_id)

                point = models.PointStruct(
                    id=transaction_id,
                    vector={"dense": dense_vectors[idx], "sparse": sparse_vectors[idx]},
                    payload=payload,
                )

                points.append(point)

            batch_size = 50
            total_loaded = 0

            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.qdrant.upsert(collection_name=self.collection_name, points=batch)
                total_loaded += len(batch)
                logger.info(f"Загружено {total_loaded}/{len(points)} точек...")

            logger.info(f"Загружено {total_loaded} транзакций в Qdrant!")

            return total_loaded

        except FileNotFoundError:
            logger.error(f"CSV файл не найден: {csv_path}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при загрузке CSV: {e}")
            raise

    def count_user_transactions(self, user_id: int) -> int:
        """
        Возвращает количество транзакций пользователя в Qdrant.

        Args:
            user_id: ID пользователя

        Returns:
            int: Количество транзакций
        """
        try:
            result = self.qdrant.count(
                collection_name=self.collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
                    ]
                ),
            )
            return result.count
        except Exception as e:
            logger.error(f"Ошибка подсчёта транзакций для user_id={user_id}: {e}")
            return 0
