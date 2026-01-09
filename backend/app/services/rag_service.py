import logging
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, NamedSparseVector, NamedVector

from app.config import DENSE_MODEL_NAME, QDRANT_COLLECTION_NAME, SPARSE_MODEL_NAME, SYSTEM_PROMPT
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG для финансового ассистента"""

    def __init__(self, qdrant: QdrantClient, embedder: EmbeddingService, llm: LLMService):
        self.qdrant = qdrant
        self.embedder = embedder
        self.llm = llm
        self.sparse_model = SPARSE_MODEL_NAME
        self.dense_model = DENSE_MODEL_NAME

    async def ask(self, query: str, user_id: int, limit: int = None) -> Dict[str, Any]:
        """
        :param query: Запрос пользователя
        :type query: str
        :param user_id: Юникальный юзер id
        :type user_id: int
        :return: ответ LLM
        :rtype: str
        """
        logger.info(f"Поиск по запросу: {query}")
        if limit is None:
            limit = self._estimate_limit(query)

        # Поиск транзакций в Qdrant
        transactions = await self._search_transactions(query, user_id, limit)

        # Формируем
        context = self._format_context(transactions)

        # 3️⃣ Создание промпта
        messages = self._build_messages(context, query)

        # 4️⃣ Вызов LLM
        answer = await self.llm.generate(messages)

        logger.info(f"RAG завершён: {len(transactions)} транзакций")

        return {
            "query": query,
            "answer": answer,
            "transactions": transactions,
            "found_count": len(transactions),
        }

    async def _search_transactions(self, query: str, user_id: int, limit: int) -> List[Dict]:
        """
        :param query: Запрос пользователя
        :type query: str
        :param user_id: Уникальный юзер id
        :type user_id: int
        :return: Необходимые транзакции после поиска
        :rtype: List[Dict]
        """
        logger.info(f"Запускаем гибридный поиск (limit={limit})")

        dense_vector = self.embedder.embed_dense(query)
        sparse_vector = self.embedder.embed_sparse(query)
        limit = self._estimate_limit(query=query)

        # DENSE ПОИСК
        try:
            dense_results = self.qdrant.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=NamedVector(
                    name="dense",
                    vector=dense_vector,
                ),
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=limit * 2,
                score_threshold=0.6,
            )

            logger.info(f"Dense поиск: {len(dense_results)} результатов")
        except Exception as e:
            logger.error(f"Dense поиск ошибка: {e}")
            dense_results = []

        # SPARSE ПОИСК
        try:
            sparse_results = self.qdrant.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=NamedSparseVector(
                    name="sparse",
                    vector=sparse_vector,
                ),
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=limit * 2,
                score_threshold=0.4,
            )
            logger.info(f"Sparse поиск: {len(sparse_results)} результатов")

        except Exception as e:
            logger.error(f"Sparse поиск ошибка: {e}")
            sparse_results = []

        if dense_results or sparse_results:
            transactions = self._rrf_fusion(dense_results, sparse_results, limit)
        else:
            logger.warning("Ни dense, ни sparse ничего не нашли")
            transactions = []

        logger.info(f"Найдено {len(transactions)} транзакций (hybrid search)")
        return transactions

    def _format_context(self, transactions: List[Dict]) -> str:
        """
        :param transactions: Все транзакции выбранные для ответа
        :type transactions: List[Dict]
        :return: Форматирует каждую тразакцию в приятный вид
        :rtype: str
        """
        # Если транзакций нет
        if not transactions:
            return "У пользователя нет соответствующих транзакций."

        # Форматируем каждую транзакцию
        context = f"Найдено {len(transactions)} релевантных транзакций:\n\n"

        for i, tx in enumerate(transactions, start=1):
            # Конвертируем amount в правильный формат
            amount_formatted = f"{tx['amount']:,.0f}".replace(",", " ")

            # Строим красивую строку для LLM
            context += (
                f"{i}. **{tx['date']}** - *{tx['category']}*\n"
                f"   Сумма: {amount_formatted}₽\n"
                f"   Описание: {tx['description']}\n"
                f"   Релевантность: {tx['rrf_score']:.1%}\n\n"
            )

        return context

    def _build_messages(self, context: str, query: str) -> List[Dict]:
        """
        :param context: Сформированный красивый контекст наших транзакций для LLM
        :type context: str
        :param query: Запрос пользователя
        :type query: str
        :return: Генерирует промпт для LLM
        :rtype: List[Dict]

        """

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nВопрос: {query}"},
        ]

        return messages

    def _estimate_limit(self, query: str) -> int:
        """
        Умное определение лимита на основе запроса.
        """

        query_lower = query.lower()

        # Агрегационные запросы (нужно много данных)
        if any(
            word in query_lower
            for word in [
                "всего",
                "итого",
                "сумма",
                "средний",
                "за месяц",
                "за год",
                "статистика",
                "сколько всего",
                "топ",
                "рейтинг",
            ]
        ):
            return 300

        # Поиск конкретных транзакций
        elif any(
            word in query_lower
            for word in ["последн", "недавн", "вчера", "сегодня", "когда", "найди"]
        ):
            return 70

        # Категориальные запросы
        elif any(
            word in query_lower
            for word in ["кафе", "рестора", "такси", "еда", "подписк", "развлечен"]
        ):
            return 100

        # По умолчанию
        else:
            return 90

    def _rrf_fusion(self, dense_results: List, sparse_results: List, k: int) -> List[Dict]:
        """
        :param dense_results: Результаты поиска ретрива
        :type dense_results: List
        :param sparse_results: Результаты поиска BM25
        :type sparse_results: List
        :param k: Количество выбранных транзакций
        :type k: int
        :return: объединенный список тразакций
        :rtype: List[Dict]
        """

        logger.info(f"RRF fusion: dense={len(dense_results)}, sparse={len(sparse_results)}")

        rrf_scores = {}

        # Добавляем RRF scores из dense результатов
        for rank, hit in enumerate(dense_results, start=1):
            point_id = str(hit.id)
            rrf_scores.setdefault(point_id, []).append(1.0 / (rank + 60))

        # Добавляем RRF scores из sparse результатов
        for rank, hit in enumerate(sparse_results, start=1):
            point_id = str(hit.id)
            rrf_scores.setdefault(point_id, []).append(1.0 / (rank + 60))

        logger.info(f"RRF: {len(rrf_scores)} уникальных транзакций")

        # Берём среднее значение RRF score
        combined_scores = []

        for point_id, score_list in rrf_scores.items():
            avg_score = sum(score_list) / len(score_list)
            combined_scores.append((point_id, avg_score))

        combined_scores.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Топ RRF scores: {combined_scores[:3]}")

        hits_dict = {}  # point_id → hit объект

        # Добавляем все hits в словарь
        for hit in dense_results:
            hits_dict[str(hit.id)] = hit

        for hit in sparse_results:
            hits_dict[str(hit.id)] = hit

        # Собираем топ-k транзакций
        transactions = []

        for point_id, rrf_score in combined_scores[:k]:
            # Ищем hit в словаре
            hit = hits_dict.get(point_id)

            if hit:
                transaction = {
                    "id": point_id,
                    "date": hit.payload.get("date", "N/A"),
                    "amount": float(hit.payload.get("amount", 0)),
                    "category": hit.payload.get("category", "Неизвестно"),
                    "description": hit.payload.get("description", ""),
                    "rrf_score": rrf_score,
                }
                transactions.append(transaction)

        logger.info(f"RRF: {len(transactions)} транзакций")
        return transactions
