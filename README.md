# SQL Genius: Agentic RAG for Enterprise SQL Generation

**SQL Genius** — это интеллектуальная система на базе LLM для генерации, тестирования и самокоррекции SQL-запросов. Проект специально спроектирован для работы с огромными базами данных (**2000+ таблиц**), где стандартные промпты не справляются из-за перегрузки контекста.



---

## Архитектура (ML System Design)

Система реализует паттерн **Agentic RAG** с использованием циклического графа состояний.

### Основные компоненты:
1.  **Semantic Retriever (ChromaDB):** Использует эмбеддинги `paraphrase-multilingual-MiniLM-L12-v2` для поиска релевантных таблиц по семантическому смыслу вопроса.
2.  **Schema Pruner:** Двухэтапная фильтрация колонок через LLM (Gemini/Llama) с использованием **Pydantic Structured Output**, что позволяет сократить контекст на 90%.
3.  **Self-Correction Loop (LangGraph):** Если сгенерированный SQL падает с ошибкой в базе, агент анализирует ошибку и делает до 3 попыток исправления.
4.  **Database Sandbox:** Локальный клон структуры БД в Docker для безопасного исполнения сгенерированного кода.

---

## Технологический стек

* **Backend:** Python 3.12-slim, FastAPI
* **AI Orchestration:** LangGraph, LangChain, Pydantic v2
* **Vector DB:** ChromaDB (HttpClient mode)
* **SQL DB:** PostgreSQL 15
* **LLM Provider:** OpenRouter (доступ к Gemini 1.5 Flash, Llama 3.1)
* **Infra:** Docker Compose

---

## Безопасность и отказоустойчивость

* **Read-Only Access:** Все запросы от LLM выполняются в изолированном контейнере под пользователем с правами `SELECT` только на необходимые таблицы.
* **DDL Surgery:** Специальный скрипт инициализации `init.sql` разделяет создание таблиц и связей (`ALTER TABLE`), что позволяет поднимать схемы с тысячами циклических зависимостей.
* **Telemetry Disable:** Отключена анонимная телеметрия ChromaDB для соблюдения приватности данных.

------

### Что мы сделали за этот сешн:
1.  **Стабилизировали Docker:** Решили проблемы с местом, версиями Python 3.12 и сетевыми DNS.
2.  **Починили SQL:** Написали «хирургический» подход для импорта схем любой сложности.
3.  **Настроили RAG:** Синхронизировали метаданные в Postgres и проиндексировали их в ChromaDB.
4.  **Запустили Агента:** Подключили LangGraph к OpenRouter.

##  Быстрый старт

### 1. Настройка окружения
Создайте файл `.env` в корне проекта:
```env
OPENROUTER_API_KEY=ваш_ключ
LOCAL_DB_URL=postgresql://app_user:app_password@db:5432/metadata_db
CHROMA_HOST=chroma
CHROMA_PORT=8000
```

###  2. Запуск контейнеров
```env
docker-compose down -v  # Очистка старых данных

docker-compose up -d --build
```
###  3. Наполнение системы (ETL)

Синхронизация метаданных из JSON в Postgres
```env
docker exec -it sql_genius_app python -m src.ingestion.sync_metadata
```
Создание векторных эмбеддингов в ChromaDB
```env
docker exec -it sql_genius_app python -m src.retriever.vector_search
```
###  4. Тестирование через API
```env
Перейдите в Swagger UI: http://localhost:8080/docs и используйте эндпоинт /api/v1/generate-sql.
```
##  Структура проекта
```env
├── data/schemas/      # Исходные метаданные БД в JSON
├── docker/            # Скрипты инициализации БД (init.sql)
├── src/
│   ├── api/           # FastAPI роуты и логика сервера
│   ├── core/          # Глобальный конфиг (Pydantic Settings)
│   ├── ingestion/     # ETL скрипты для миграции метаданных
│   ├── retriever/     # Логика работы с ChromaDB
│   ├── services/      # LangGraph Агент и LLM-клиент
│   └── schemas/       # Pydantic модели (Input/Output контракты)
├── Dockerfile         # Оптимизированный образ на Python 3.12
└── docker-compose.yml # Оркестрация всей инфраструктуры
```
---

##  Построенный граф

![png](/materials/mermaid-drawing.png)

### Было сделало следующее:


1.  **Стабилизирован Docker:** Решили проблемы с местом, версиями Python 3.12 и сетевыми DNS.
2.  **Починил SQL:** Написали «хирургический» подход для импорта схем любой сложности.
3.  **Настроил RAG:** Синхронизировали метаданные в Postgres и проиндексировали их в ChromaDB.
4.  **Запустил Агента:** Подключили LangGraph к OpenRouter.