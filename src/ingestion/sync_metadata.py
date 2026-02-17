import psycopg2
from src.core.config import settings

def sync_local_metadata():
    """Считывает структуру public-схемы и сохраняет её в таблицы метаданных."""
    query = """
    SELECT 
        cols.table_schema, 
        cols.table_name, 
        cols.column_name, 
        cols.data_type,
        'Описание для ' || cols.column_name as column_comment, -- Заглушка, если нет комментов
        'Таблица ' || cols.table_name as table_comment
    FROM 
        information_schema.columns cols
    WHERE 
        cols.table_schema = 'public' 
        AND cols.table_name NOT IN ('table_metadata', 'column_metadata')
    ORDER BY cols.table_name, cols.ordinal_position;
    """
    
    try:
        conn = psycopg2.connect(settings.LOCAL_DB_URL)
        with conn:
            with conn.cursor() as cur:
                # 1. Читаем структуру
                cur.execute(query)
                rows = cur.fetchall()
                
                # 2. Собираем уникальные таблицы
                tables = set((r[0], r[1], r[5]) for r in rows)
                for schema, name, desc in tables:
                    cur.execute("""
                        INSERT INTO table_metadata (schema_name, table_name, table_description)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (schema_name, table_name) DO UPDATE SET table_description = EXCLUDED.table_description
                    """, (schema, name, desc))

                # 3. Мапим имена на ID
                cur.execute("SELECT id, table_name FROM table_metadata")
                table_map = {name: tid for tid, name in cur.fetchall()}

                # 4. Вставляем колонки
                for r in rows:
                    cur.execute("""
                        INSERT INTO column_metadata (table_id, column_name, data_type, column_description)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (table_map[r[1]], r[2], r[3], r[4]))
                    
        print(f"Успешно синхронизировано {len(tables)} таблиц.")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    sync_local_metadata()