# src/services/sql_generator.py
import openrouter  # Или используй стандартный openai клиент для OpenRouter
from chromadb.utils import embedding_functions
import chromadb
from src.core.config import settings

class SQLGenerator:
    def __init__(self):
        # Подключаемся к нашей "карте" (ChromaDB)
        self.chroma_client = chromadb.HttpClient(host='localhost', port=8000)
        
        # Модель должна быть той же, что и при индексации!
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.collection = self.chroma_client.get_collection(
            name="table_schemas", 
            embedding_function=self.emb_fn
        )

    def run_query(self, sql: str):
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    # Нам не нужны все данные, возьмем только 5 строк для проверки
                    res = cur.fetchmany(5)
                    return {"status": "success", "sample_data": res}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    def _get_relevant_schemas(self, user_query: str, n_results: int = 5):
        """Шаг 1: Достаем из ChromaDB самые похожие таблицы."""
        results = self.collection.query(
            query_texts=[user_query],
            n_results=n_results
        )
        # Возвращаем список описаний найденных таблиц
        return results['documents'][0]

    def generate_sql(self, user_question: str):
        # 1. Находим релевантные куски схемы
        schemas = self._get_relevant_schemas(user_question)
        context_schema = "\n\n".join(schemas)

        # 2. Строим промпт (это "инструкция" для нашего повара)
        system_prompt = f"""
        Ты — Staff SQL Engineer. Твоя задача — писать только валидные SQL запросы для PostgreSQL.
        Используй предоставленные ниже схемы таблиц. 
        Если данных недостаточно, скажи об этом.
        
        СХЕМЫ ТАБЛИЦ:
        {context_schema}
        """

        # 3. Отправляем в OpenRouter (пример через абстрактный клиент)
        # Тут ты выберешь модель, например, 'anthropic/claude-3-haiku' или 'google/gemini-pro-1.5'
        # Они отлично справляются с Text-to-SQL
        print(f"--- Генерирую SQL для вопроса: {user_question} ---")
        
        # Логика вызова API OpenRouter...
        # return response.choices[0].message.content
        return "SELECT * FROM ... (здесь будет ответ от LLM)"