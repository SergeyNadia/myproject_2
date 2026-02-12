# src/api/routes.py
from fastapi import APIRouter, HTTPException
from src.schemas.models import SQLResponse
from src.services.graph_agent import SQLGraphAgent

router = APIRouter()
agent = SQLGraphAgent() # Инициализируем наш "мозг"

@router.post("/generate-sql", response_model=SQLResponse)
async def generate_sql_endpoint(user_query: str):
    """
    Принимает вопрос на естественном языке и возвращает проверенный SQL.
    """
    try:
        # Запускаем наш LangGraph
        # На выходе мы ожидаем финальное состояние графа
        result = await agent.run(user_query)
        
        if not result.get("generated_sql"):
            raise HTTPException(status_code=422, detail="Не удалось сгенерировать валидный SQL")
            
        return SQLResponse(
            sql_query=result["generated_sql"],
            explanation=result.get("explanation", "Запрос успешно сгенерирован и проверен.")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))