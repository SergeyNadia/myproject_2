# Используем легковесный образ Python, соответствующий вашей версии
FROM python:3.11-slim

# Устанавливаем системные зависимости для работы с Excel и SQLite (нужно для Chroma)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Сначала копируем только requirements, чтобы Docker закешировал установку библиотек
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Команда по умолчанию (запуск индексации)
CMD ["python", "incialization.py"]