# src/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Данные берем из .env автоматически
    SOURCE_DB_URL: str
    LOCAL_DB_URL: str
    OPENROUTER_API_KEY: str
    LOG_LEVEL: str = "INFO" 
    
    class Config:
        env_file = ".env"

settings = Settings()