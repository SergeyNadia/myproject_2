# Используем легковесный образ Python 3.12
FROM python:3.12-slim-bookworm

# Устанавливаем системные зависимости для psycopg2 и работы с сетью
RUN apt-get update -o Acquire::ForceIPv4=true && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Сначала копируем только requirements, чтобы использовать кэширование слоев Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

# Открываем порт для FastAPI
EXPOSE 8080

# Команда для запуска (через модуль src.api.main)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]