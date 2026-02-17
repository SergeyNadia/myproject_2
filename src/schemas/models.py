from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional


class ColumnSelection(BaseModel):
    table_name: str = Field(description="Название таблицы")
    relevant_columns: List[str] = Field(description="Список только тех колонок, которые нужны для ответа")
    reasoning: str = Field(description="Почему выбраны эти колонки")

class TableFilterResponse(BaseModel):
    selected_tables: List[ColumnSelection]

class SQLResponse(BaseModel):
    # Модель поймет и 'sql_query', и просто 'sql'
    sql_query: str = Field(
        validation_alias=AliasChoices('sql_query', 'sql'),
        description="Валидный PostgreSQL запрос"
    )
    # Делаем поле необязательным, чтобы не падать, если модель его забыла
    explanation: Optional[str] = Field(
        default="Описание не предоставлено",
        description="Краткое описание запроса"
    )