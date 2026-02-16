# src/ingestion/sync_metadata.py
import json
import psycopg2
import os
from psycopg2.extras import execute_values
from src.core.config import settings


def sync_from_json(json_path: str):
    # Проверка пути (для отладки)
    full_path = os.path.abspath(json_path)
    if not os.path.exists(full_path):
        print(f"ОШИБКА: Файл не найден по пути {full_path}")
        print(f"Текущая рабочая директория: {os.getcwd()}")
        return
    
    """Загрузка метаданных из JSON-файла в локальную БД."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Извлекаем список строк (значение по ключу с SQL-запросом)
    # Берем первый ключ, так как в твоем файле SQL-запрос — это ключ
    first_key = list(data.keys())[0]
    rows = data[first_key]

    print(f"--- Найдено {len(rows)} записей о колонках ---")

    try:
        conn = psycopg2.connect(settings.LOCAL_DB_URL)
        with conn:
            with conn.cursor() as cur:
                # 1. Собираем уникальные таблицы
                tables = {}
                for r in rows:
                    key = (r['table_schema'], r['table_name'])
                    if key not in tables:
                        tables[key] = r['table_comment']
                
                # 2. Вставляем таблицы
                table_data = [(s, t, c) for (s, t), c in tables.items()]
                execute_values(cur, """
                    INSERT INTO table_metadata (schema_name, table_name, table_description)
                    VALUES %s ON CONFLICT (schema_name, table_name) DO UPDATE 
                    SET table_description = EXCLUDED.table_description
                """, table_data)

                # 3. Мапим имена таблиц на ID
                cur.execute("SELECT id, schema_name, table_name FROM table_metadata")
                table_map = {(row[1], row[2]): row[0] for row in cur.fetchall()}

                # 4. Вставляем колонки
                col_data = [
                    (table_map[(r['table_schema'], r['table_name'])], r['column_name'], ...)
                    for r in rows if (r['table_schema'], r['table_name']) in table_map
                ]
                execute_values(cur, """
                    INSERT INTO column_metadata (table_id, column_name, data_type, column_description)
                    VALUES %s ON CONFLICT DO NOTHING
                """, col_data)

        print(f"--- Успешно синхронизировано {len(tables)} таблиц ---")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

if __name__ == "__main__":
    sync_from_json('data/schemas/tula-db2(public).json')