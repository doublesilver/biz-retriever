from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application Settings
    """
    PROJECT_NAME: str = "Biz-Retriever Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 Days

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_PASSWORD: Union[str, None] = None

    # OpenAI (선택)
    OPENAI_API_KEY: Union[str, None] = None

    # Google Gemini API (AI 분석 - 권장)
    GEMINI_API_KEY: Union[str, None] = None

    # Phase 1: G2B API (나라장터) - 데이터셋 개방표준 서비스
    G2B_API_KEY: Union[str, None] = None
    G2B_API_ENDPOINT: str = "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo"

    # Phase 1: Slack Notification
    SLACK_WEBHOOK_URL: Union[str, None] = None
    SLACK_CHANNEL: str = "#입찰-알림"

    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]
    PRODUCTION_DOMAIN: Union[str, None] = None

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL with optional password"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct SQLAlchemy Database URI"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def DATABASE_URL(self) -> str:
        """Alias for SQLALCHEMY_DATABASE_URI (used by Alembic)"""
        return self.SQLALCHEMY_DATABASE_URI
    
    @property
    def CELERY_BROKER_URL(self) -> str:
        """Construct Celery Broker URL"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Construct Celery Result Backend URL"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
