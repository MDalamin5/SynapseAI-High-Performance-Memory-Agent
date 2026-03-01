from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    REDIS_URL: str = "redis://localhost:6379/0" # Default if not in .env

    class Config:
        env_file = ".env"

settings = Settings()