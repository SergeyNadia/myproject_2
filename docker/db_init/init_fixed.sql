-- I. ИНФРАСТРУКТУРА (Системные таблицы нашего RAG-а)
CREATE TABLE IF NOT EXISTS table_metadata (
    id SERIAL PRIMARY KEY,
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    table_description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(schema_name, table_name)
);

CREATE TABLE IF NOT EXISTS column_metadata (
    id SERIAL PRIMARY KEY,
    table_id INTEGER REFERENCES table_metadata(id) ON DELETE CASCADE,
    column_name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    column_description TEXT,
    is_primary_key BOOLEAN DEFAULT FALSE,
    UNIQUE(table_id, column_name)
);

-- II. БИЗНЕС-ДАННЫЕ (Твои 5 таблиц)
CREATE TABLE IF NOT EXISTS public.databaseinfo (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50),
    description TEXT
);

CREATE TABLE IF NOT EXISTS public.f2 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS public.f6 (
    id SERIAL PRIMARY KEY,
    f2_id INTEGER REFERENCES public.f2(id),
    document_number VARCHAR(100),
    reg_date DATE
);

CREATE TABLE IF NOT EXISTS public.f17 (
    id SERIAL PRIMARY KEY,
    f6_id INTEGER REFERENCES public.f6(id),
    amount NUMERIC(15, 2)
);

CREATE TABLE IF NOT EXISTS public.f6izm (
    id SERIAL PRIMARY KEY,
    f6_id INTEGER REFERENCES public.f6(id),
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);