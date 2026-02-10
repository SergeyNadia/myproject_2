import chromadb
from chromadb.utils import embedding_functions

# Подключаемся к базе
client = chromadb.PersistentClient(path="./chroma_db_store")
embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
collection = client.get_collection(name="sql_schema_collection", embedding_function=embedding_model)

# ТЕСТ: Ищем по смыслу, а не по названию
query = "Выведи граждан с действующим признаком учета 'Дети-сироты' с таблицы f1"
results = collection.query(query_texts=[query], n_results=3)

for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
    print(f"\n--- РЕЗУЛЬТАТ {i+1} (Таблица: {metadata['tname']}) ---")
    print(doc[:500] + "...") # Печатаем первые 500 символов карточки