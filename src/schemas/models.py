from pydantic import BaseModel, Field
from typing import List

class ColumnSelection(BaseModel):
    table_name: str = Field(description="Название таблицы")
    relevant_columns: List[str] = Field(description="Список только тех колонок, которые нужны для ответа")
    reasoning: str = Field(description="Почему выбраны эти колонки")

class TableFilterResponse(BaseModel):
    selected_tables: List[ColumnSelection]

class SQLResponse(BaseModel):
    sql_query: str = Field(description="Валидный PostgreSQL запрос")
    explanation: str = Field(description="Краткое описание того, что делает запрос")