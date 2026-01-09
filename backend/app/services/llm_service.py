import logging
import os

from openai import AsyncOpenAI

from app.config import API_KEY, BASE_URL, LLM_MODEL_NAME

logger = logging.getLogger(__name__)


class LLMService:
    """
    Docstring для LLMService
    Простой класс для вызова LLM
    """

    def __init__(self):
        api_key = API_KEY
        if not api_key:
            raise ValueError("API_KEY не найден!")

        self.client = AsyncOpenAI(
            base_url=BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/nktrudik/finance_app",
                "X-Title": "Finly Demo",
            },
        )

    async def generate(self, messages, model=LLM_MODEL_NAME):
        """
        Docstring для generate

        :param messages: Вопрос пользователя
        :param model: модель
        :return: Ответ LLM с учетом контекста
        """
        try:
            response = await self.client.chat.completions.create(
                model=model, messages=messages, temperature=0.5, max_tokens=500
            )
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens
            logger.info(f"LLM ответил ({tokens} токенов)")
            return answer

        except Exception as e:
            logger.error(f"Генерация не состоялась, ошибка: {e}")
            raise
