from fastembed import SparseTextEmbedding, TextEmbedding
from app.config import DENSE_MODEL_NAME, SPARSE_MODEL_NAME, MODELS_DIR, BATCH_SIZE
import logging, hashlib, pickle
from typing import List, Dict, Tuple
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Docstring для EmbeddingService
    Класс для создания эмбэддингов
    """

    def __init__(self, cache_dir: str = MODELS_DIR, batch_size: int = BATCH_SIZE):
        """
        Docstring для __init__
        
        :param cache_dir: Папка для хранения моделей и коллекций
        :type cache_dir: str
        :param batch_size: Размер бача для загрузки эмбэддингов в Qdrant
        :type batch_size: int
        """
        # Папка уже создана в config.py, здесь только логируем
        logger.info("Инициализация embedding моделей...")
        logger.info(f"Кэш моделей: {MODELS_DIR}")
        
        self.cache_dir = cache_dir
        # Dense embeddings
        self.dense_model = TextEmbedding(
            model_name=DENSE_MODEL_NAME,
            cache_dir=self.cache_dir
        )
        logger.info(f"Dense model {MODELS_DIR} загружена")
        
        # Sparse embeddings
        self.sparse_model = SparseTextEmbedding(
            model_name=SPARSE_MODEL_NAME,
            cache_dir=self.cache_dir
        )

        logger.info(f"Sparse model {SPARSE_MODEL_NAME} загружена")

        self.batch_size = batch_size
    
    def embed_dense(self, text: str) -> List[float]:
        """
        Docstring для embed_dense
        
        :param text: Запрос пользователя
        :type text: str
        :return: Эмбэддинг запроса (семантический)
        :rtype: List[float]
        """
        embeddings = list(self.dense_model.embed([text]))
        return embeddings[0].tolist()

    def embed_sparse(self, text: str) -> Dict:
        """
        Docstring для embed_sparse
        
        :param text: Запрос пользователя
        :type text: str
        :return: Эмбэддинг запроса (лексический)
        :rtype: Dict
        """
        embeddings = list(self.sparse_model([text]))
        sparse_vector = embeddings[0]

        return {
            "indices": sparse_vector.indices.tolist(),
            "values": sparse_vector.values.tolist()
        }
    
    def _get_cache_key(self, texts: List[str]) -> str:
        """
        Docstring для _get_cache_key
        
        :param texts: Все эмбэддинги транзакций
        :type texts: List[str]
        :return: возвращает кэш для файла транзакций
        :rtype: str
        """
        text_hash = hashlib.sha256("".join(texts).encode()).hexdigest()
        return f"embeddings_{text_hash[:16]}.pkl"

    def _load_from_cache(self, cache_key: str):
        """
        Docstring для _load_from_cache
        
        :param cache_key: Уникальный ключ транзакций
        :type cache_key: str
        """
        cache_path = self.cache_dir / cache_key

        if cache_path.exists():
            try:
                logger.info(f"Загрузка эмбеддингов из кэша: {cache_key}")
                with open(file=cache_path, mode="rb") as f:
                    data = pickle.load(f)
                    return data['dense'], data['sparse']
            
            except Exception as e:
                logger.warning(f"⚠️ Ошибка чтения кэша: {e}, регенерация...")
                cache_path.unlink(missing_ok=True)

        return None

    def _save_to_cache(
            self, 
            cache_key: str, 
            dense_vectors: List[List[float]],
            sparse_vectors: List[List[float]]
    ):
        """
        Docstring для _save_to_cache
        
        :param cache_key: Уникальный ключ-кэш для тразакций
        :type cache_key: str
        :param dense_vectors: Список смысловых эмбэддингов
        :type dense_vectors: List[List[float]]
        :param sparse_vectors: Список лексических эмбэддигов
        :type sparse_vectors: List[List[float]]
        """

        cache_path = self.cache_dir /  cache_key
        try:
            logger.info(f"Сохранение эмбеддингов в кэш: {cache_key}")

            with open(file=cache_path, mode='wb') as f:
                pickle.dump({
                    "dense": dense_vectors,
                    "sparse": sparse_vectors
                },f,
                protocol=pickle.HIGHEST_PROTOCOL)
                logger.info(f"Кэш сохранён: {cache_path.stat().st_size / 1024 / 1024:.2f} MB")
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша: {e}")


    def embed_batch(self, texts: List[str], use_cache: bool = True) -> Tuple[List[List[float]], List[Dict]]:
        """
        Docstring для embed_batch

        :param texts: Запрос пользователя
        :type texts: List[str]
        :param use_cache: Используем кэш (если тразакции уже в хранилище)
        :type use_cache: bool
        :return: Кортеж из семантического и лексического эмбэддингов
        :rtype: Tuple[List[List[float]], List[Dict]]
        """
        logger.info(f"Генерация эмбеддингов для {len(texts)} текстов...")
        dense_vectors = []
        sparse_vectors = []
        
        if not texts:
            return [], []
        
        if use_cache:
            cache_key = self._get_cache_key(texts)
            cached = self._load_from_cache(cache_key)
            
            if cached is not None:
                return cached
        
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Генерация эмбеддингов"):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"  Батч {batch_num}/{total_batches}: обработка {len(batch)} текстов...")
            
            # Dense embeddings для батча
            dense_batch = list(self.dense_model.embed(batch))
            dense_vectors.extend([emb.tolist() for emb in dense_batch])
            
            # Sparse embeddings для батча
            sparse_batch = list(self.sparse_model.embed(batch))
            sparse_vectors.extend([
                {
                    "indices": emb.indices.tolist(),
                    "values": emb.values.tolist()
                }
                for emb in sparse_batch
            ])
            
        logger.info("Эмбеддинги сгенерированы")

        if use_cache:
            self._save_to_cache(cache_key, dense_vectors, sparse_vectors)
        
        return dense_vectors, sparse_vectors