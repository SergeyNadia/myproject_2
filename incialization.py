import chromadb
from chromadb.utils import embedding_functions
import json
import os

# --- КОНФИГУРАЦИЯ ПУТЕЙ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "db_metadata")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db_store")

HIERARCHY_FILE = os.path.join(DATA_DIR, "db_schema_hierarchy.json")
RELATIONS_FILE = os.path.join(DATA_DIR, "schema_relations.json")

# 1. Инициализация ChromaDB
client = chromadb.PersistentClient(path=CHROMA_PATH)
embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

collection = client.get_or_create_collection(
    name="sql_schema_collection",
    embedding_function=embedding_model,
    metadata={"hnsw:space": "cosine"}
)

# 2. Загрузка подготовленных данных
if not os.path.exists(HIERARCHY_FILE):
    print(f"❌ ОШИБКА: Файл не найден по пути {HIERARCHY_FILE}")
    exit()

with open(HIERARCHY_FILE, 'r', encoding='utf-8') as f:
    hierarchy = json.load(f)
    print(f"🔍 Загружено из JSON: {len(hierarchy)} таблиц.")

relations = {}
if os.path.exists(RELATIONS_FILE):
    with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
        relations = json.load(f)

# 3. Формирование карточек
table_profiles = []

for tname, info in hierarchy.items():
    cols_text = []
    for col in info.get('columns', []):
        # Используем ваши ключи: fname, ftype, title
        f_name = col.get('fname', 'unknown_col')
        f_type = col.get('ftype', 'unknown_type')
        f_title = col.get('title', 'без описания')
        cols_text.append(f"- {f_name} ({f_type}): {f_title}")
    
    rel_text = []
    if tname in relations:
        for rel in relations[tname]:
            # ИСПОЛЬЗУЕМ ВАШИ КЛЮЧИ ИЗ schema_relations.json: column, referred_table, referred_column
            src = rel.get('column')
            dst_t = rel.get('referred_table')
            dst_c = rel.get('referred_column')
            
            if src and dst_t and dst_c:
                rel_text.append(f"- {src} -> {dst_t}.{dst_c}")
    
    content = [f"Table: {tname}", "Columns:", "\n".join(cols_text)]
    if rel_text:
        content.append("Relationships (Foreign Keys):")
        content.append("\n".join(rel_text))
        
    table_card = "\n".join(content)
    
    table_profiles.append({
        "id": f"table_{tname}",
        "content": table_card,
        "metadata": {"tname": tname}
    })

# 4. Индексация
if not table_profiles:
    print("❌ ОШИБКА: Список профилей пуст. Нечего индексировать.")
else:
    documents = [p['content'] for p in table_profiles]
    metadatas = [p['metadata'] for p in table_profiles]
    ids = [p['id'] for p in table_profiles]

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
            ids=ids[i:i + batch_size]
        )
    print(f"✅ Успешно проиндексировано {collection.count()} таблиц.")