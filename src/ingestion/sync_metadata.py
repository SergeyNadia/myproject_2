# src/ingestion/sync_metadata.py
import psycopg2
from psycopg2.extras import execute_values
from src.core.config import settings

def fetch_source_metadata():
    """Вытягиваем структуру из 'боевой' базы."""
    query = """
    SELECT 
        cols.table_schema, 
        cols.table_name, 
        cols.column_name, 
        cols.data_type,
        pg_catalog.col_description(c.oid, cols.ordinal_position::int) AS column_comment,
        pg_catalog.obj_description(c.oid, 'pg_class') AS table_comment
    FROM 
        information_schema.columns cols
    JOIN 
        pg_class c ON c.relname = cols.table_name
    JOIN 
        pg_namespace n ON n.oid = c.relnamespace AND n.nspname = cols.table_schema
    WHERE 
        cols.table_schema = 'public' 
    ORDER BY cols.table_name, cols.ordinal_position;
    """
    try:
        with psycopg2.connect(settings.SOURCE_DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()
    except Exception as e:
        print(f"Ошибка при чтении из боевой базы: {e}")
        return []

def sync_all():
    """Главная точка входа для синхронизации метаданных и данных."""
    try:
        source_conn = psycopg2.connect(settings.SOURCE_DB_URL)
        local_conn = psycopg2.connect(settings.LOCAL_DB_URL)
        
        with source_conn, local_conn:
            with source_conn.cursor() as s_cur, local_conn.cursor() as l_cur:
                # 1. Получаем список всех таблиц и колонок
                print("--- ШАГ 1: Чтение структуры из боевой базы ---")
                s_cur.execute("""
                    SELECT table_schema, table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public';
                """)
                columns_data = s_cur.fetchall()
                
                # 2. Группируем колонки по таблицам для создания структуры
                tables_dict = {}
                for schema, table, col, dtype in columns_data:
                    full_name = f"{schema}.{table}"
                    if full_name not in tables_dict:
                        tables_dict[full_name] = []
                    tables_dict[full_name].append(f"{col} {dtype}")

                # 3. Создаем таблицы и копируем данные (Вариант А)
                print(f"--- ШАГ 2: Клонирование {len(tables_dict)} таблиц ---")
                for table_full_name, columns in tables_dict.items():
                    # Создаем таблицу в Docker (если нет)
                    cols_str = ", ".join(columns)
                    l_cur.execute(f"CREATE TABLE IF NOT EXISTS {table_full_name} ({cols_str});")
                    
                    # Очищаем старый слепок и берем 100 новых строк
                    l_cur.execute(f"TRUNCATE {table_full_name};")
                    
                    # Копируем данные (анонимизацию можно вставить здесь)
                    s_cur.execute(f"SELECT * FROM {table_full_name} LIMIT 100;")
                    rows = s_cur.fetchall()
                    
                    if rows:
                        placeholders = ",".join(["%s"] * len(rows[0]))
                        insert_query = f"INSERT INTO {table_full_name} VALUES ({placeholders})"
                        l_cur.executemany(insert_query, rows)

                # 4. Обновляем метаданные для LLM (как мы писали ранее)
                # ... тут логика заполнения table_metadata и column_metadata ...
                
        print("--- СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА ---")
    except Exception as e:
        print(f"Критическая ошибка ETL: {e}")
    finally:
        source_conn.close()
        local_conn.close()

def save_to_local_db(data):
    """Сохраняем в нашу 'теневую' базу в Docker."""
    if not data:
        return

    # Логика: сначала сохраняем таблицы, потом колонки
    # Для скорости используем SET (множество), чтобы не дублировать таблицы
    tables = set((row[0], row[1], row[5]) for row in data)
    
    try:
        with psycopg2.connect(settings.LOCAL_DB_URL) as conn:
            with conn.cursor() as cur:
                # 1. Заполняем table_metadata (используем ON CONFLICT для обновлений)
                table_insert_query = """
                INSERT INTO table_metadata (schema_name, table_name, table_description)
                VALUES %s
                ON CONFLICT (schema_name, table_name) 
                DO UPDATE SET table_description = EXCLUDED.table_description;
                """
                execute_values(cur, table_insert_query, list(tables))

                # 2. Получаем ID созданных таблиц, чтобы связать с колонками
                cur.execute("SELECT id, table_name FROM table_metadata")
                table_map = {name: tid for tid, name in cur.fetchall()}

                # 3. Подготавливаем данные для колонок
                columns_to_insert = [
                    (table_map[row[1]], row[2], row[3], row[4]) 
                    for row in data
                ]

                # 4. Заполняем column_metadata
                column_insert_query = """
                INSERT INTO column_metadata (table_id, column_name, data_type, column_description)
                VALUES %s
                ON CONFLICT DO NOTHING; -- Или UPDATE, если нужно обновлять типы
                """
                execute_values(cur, column_insert_query, columns_to_insert)
                
            conn.commit()
            print(f"Успешно синхронизировано {len(tables)} таблиц.")
    except Exception as e:
        print(f"Ошибка при записи в локальную базу: {e}")

if __name__ == "__main__":
    print("Начинаю синхронизацию...")
    raw_data = fetch_source_metadata()
    save_to_local_db(raw_data)