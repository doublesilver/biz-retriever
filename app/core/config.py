from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application Settings
    """
    PROJECT_NAME: str
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 Days
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: str

    # OpenAI
    OPENAI_API_KEY: Union[str, None] = None
    
    # Phase 1: G2B API (나라장터)
    G2B_API_KEY: Union[str, None] = None
    G2B_API_ENDPOINT: str = "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServc01"
    
    # Phase 1: Slack Notification
    SLACK_WEBHOOK_URL: Union[str, None] = None
    SLACK_CHANNEL: str = "#입찰-알림"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct SQLAlchemy Database URI"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
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
