from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
class Settings(BaseSettings):
    PROJECT_NAME: str = "LogPose AI"
    API_V1_STR: str = "/api/v1"
    
    # Security
    JWT_SECRET_KEY: str = Field(default="SUPER_SECRET_LOGPOSE_KEY_CHANGE_ME_IN_PRODUCTION")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 Days
    
    # Databases
    DATABASE_URL: str = Field(default="postgresql+asyncpg://logpose_user:logpose_password@localhost:5432/logpose_db")
    REDIS_URL: str = Field(default="redis://localhost:6379")
    
    # AI Models
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    MODEL_PLANNER: str = "deepseek-r1"
    MODEL_CODER: str = "qwen2.5-coder"
    MODEL_ROUTER: str = "qwen2.5"
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True,
        extra="ignore"
    )
settings = Settings()