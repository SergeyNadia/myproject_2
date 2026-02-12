# src/retriever/indexer.py
import chromadb
from chromadb.utils import embedding_functions
import psycopg2
from src.core.config import settings

def get_metadata_from_db():
    """Вытаскиваем то, что мы синхронизировали в локальную БД."""
    query = """
    SELECT 
        tm.id, 
        tm.schema_name, 
        tm.table_name, 
        tm.table_description,
        STRING_AGG(cm.column_name || ' (' || cm.column_description || ')', ', ') as columns_info
    FROM table_metadata tm
    JOIN column_metadata cm ON tm.id = cm.table_id
    GROUP BY tm.id;
    """
    with psycopg2.connect(settings.LOCAL_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

def create_vector_index():
    # 1. Инициализируем ChromaDB (она должна быть запущена в Docker)
    client = chromadb.HttpClient(host='localhost', port=8000)
    
    # 2. Выбираем модель эмбеддингов. 
    # Для русского языка хорошо подойдет что-то вроде 'paraphrase-multilingual-MiniLM-L12-v2'
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    collection = client.get_or_create_collection(
        name="table_schemas", 
        embedding_function=emb_fn
    )

    rows = get_metadata_from_db()
    
    documents = []
    metadatas = []
    ids = []

    for row in rows:
        tid, schema, table, desc, cols = row
        
        # Формируем "текстовый отпечаток" таблицы
        # Мы смешиваем имя, описание и инфо о колонках
        full_text = f"Table: {schema}.{table}. Description: {desc}. Columns: {cols}"
        
        documents.append(full_text)
        metadatas.append({"schema": schema, "table": table})
        ids.append(str(tid))

    # Загружаем всё в ChromaDB
    # execute_values здесь не нужен, у Chroma свой эффективный batching
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Индексация завершена. В базе {collection.count()} таблиц.")

if __name__ == "__main__":
    create_vector_index()