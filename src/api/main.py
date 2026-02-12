# src/api/main.py
from fastapi import FastAPI
from src.api.routes import router as api_router
from src.core.config import settings

app = FastAPI(
    title="SQL Genius RAG",
    description="Система генерации SQL на основе 2000 таблиц с самокоррекцией",
    version="1.0.0"
)

# Подключаем наши маршруты
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "alive", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)