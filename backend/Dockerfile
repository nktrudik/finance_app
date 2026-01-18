FROM python:3.11-slim

WORKDIR /app

# 3. Системные зависимости (для проверки состояния контейнера)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем все зависимости из бэкенда
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY ./app ./app
COPY manage.py .

# Создаём необходимые директории
RUN mkdir -p /app/data /app/logs /app/models /app/temp

# Открываем порт
EXPOSE 8000

# Healthcheck (опциаонально)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
