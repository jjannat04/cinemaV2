from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/cinemaseat"
    
    # Gateway
    GATEWAY_URL: str = "http://gateway:9000"
    
    # Application
    HOLD_TTL_SECONDS: int = 300  # 5 minutes default
    APP_PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()