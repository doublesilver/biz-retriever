from typing import List, Optional, Union
import logging

from pydantic import AnyHttpUrl, model_validator, validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application Settings with Vercel-specific configuration
    """

    PROJECT_NAME: str = "Biz-Retriever"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 Days
    FRONTEND_URL: str = "http://localhost:8081"

    # Environment
    DEBUG: bool = False  # Set to False in production
    SQL_ECHO: bool = False  # SQL query logging (disable in production)

    # Vercel Environment Detection
    VERCEL: Optional[str] = None  # "1" when deployed on Vercel
    VERCEL_ENV: Optional[str] = None  # "production" | "preview" | "development"
    VERCEL_URL: Optional[str] = None  # Deployment URL (e.g., "my-app.vercel.app")

    # Database (Priority: NEON_DATABASE_URL > DATABASE_URL > POSTGRES_URL > individual settings)
    DATABASE_URL: Optional[str] = None  # Neon/Vercel Postgres pooled connection
    NEON_DATABASE_URL: Optional[str] = None  # Explicit Neon database URL
    POSTGRES_URL: Optional[str] = None  # Vercel Postgres (legacy)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "biz_retriever"
    POSTGRES_PORT: str = "5432"

    # Redis (Priority: UPSTASH_REDIS_URL > KV_URL > REDIS_URL > individual settings)
    REDIS_URL: Optional[str] = None  # Generic Redis URL
    UPSTASH_REDIS_URL: Optional[str] = None  # Upstash Redis for serverless
    KV_URL: Optional[str] = None  # Vercel KV (Redis-compatible)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    REDIS_PASSWORD: Optional[str] = None

    # Cache TTL Settings (seconds)
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_SHORT_TTL: int = 60  # 1 minute
    CACHE_LONG_TTL: int = 3600  # 1 hour

    # OpenAI (선택)
    OPENAI_API_KEY: Union[str, None] = None

    # Google Gemini API (AI 분석 - 권장)
    GEMINI_API_KEY: Union[str, None] = None

    # OAuth2 Social Login - REMOVED
    # Kakao and Naver OAuth2 have been removed for security and maintenance simplicity

    # Phase 1: G2B API (나라장터) - 데이터셋 개방표준 서비스
    G2B_API_KEY: Union[str, None] = None
    G2B_API_ENDPOINT: str = (
        "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo"
    )
    G2B_RESULT_API_ENDPOINT: str = (
        "https://apis.data.go.kr/1230000/OpengResultService/getOpengResultInfoListSet"
    )

    # Phase 1: Slack Notification
    SLACK_WEBHOOK_URL: Union[str, None] = None
    SLACK_CHANNEL: str = "#입찰-알림"

    # Phase 8: Email Notification (SendGrid)
    SENDGRID_API_KEY: Union[str, None] = None
    SENDGRID_FROM_EMAIL: str = "noreply@biz-retriever.com"
    SENDGRID_FROM_NAME: str = "Biz-Retriever"

    # Phase 3: Payment Gateway (Tosspayments)
    TOSSPAYMENTS_SECRET_KEY: Union[str, None] = None
    TOSSPAYMENTS_CLIENT_KEY: Union[str, None] = None

    # CORS Settings
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "https://leeeunseok.tail32c3e2.ts.net",
        "https://biz-retriever.vercel.app",  # Vercel Production
        "https://biz-retriever-doublesilvers-projects.vercel.app",  # Vercel Auto Domain
        "https://biz-retriever-git-master-doublesilvers-projects.vercel.app",  # Vercel Branch
    ]
    PRODUCTION_DOMAIN: Union[str, None] = None

    @property
    def get_redis_url(self) -> Optional[str]:
        """
        Get Redis URL with priority: UPSTASH_REDIS_URL > KV_URL > REDIS_URL > local config
        
        Returns:
            Redis connection URL or None if no Redis is configured
        """
        if self.UPSTASH_REDIS_URL:
            return self.UPSTASH_REDIS_URL
        if self.KV_URL:
            return self.KV_URL
        if self.REDIS_URL:
            return self.REDIS_URL
        # Fallback to local Redis configuration
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Construct SQLAlchemy Database URI with Vercel/Neon support.
        
        Priority: NEON_DATABASE_URL > DATABASE_URL > POSTGRES_URL > individual settings
        
        For Neon Postgres with pgbouncer (connection pooling):
        - Automatically adds ?pgbouncer=true when on Vercel
        - Supports both postgresql:// and postgres:// schemes
        """
        # Priority 1: Explicit Neon database URL
        if self.NEON_DATABASE_URL:
            url = self.NEON_DATABASE_URL
        # Priority 2: Generic DATABASE_URL (Vercel Postgres, Neon, etc.)
        elif self.DATABASE_URL:
            url = self.DATABASE_URL
        # Priority 3: Legacy POSTGRES_URL (Vercel Postgres)
        elif self.POSTGRES_URL:
            url = self.POSTGRES_URL
        # Priority 4: Build from individual settings (local development)
        else:
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

        # Normalize scheme: postgres:// → postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Add pgbouncer parameter for Neon connection pooling on Vercel
        if self.VERCEL == "1":
            if "?" not in url:
                url += "?pgbouncer=true"
            elif "pgbouncer" not in url:
                url += "&pgbouncer=true"

        return url

    @property
    def CELERY_BROKER_URL(self) -> str:
        """Construct Celery Broker URL"""
        redis_url = self.get_redis_url
        if redis_url:
            return redis_url
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Construct Celery Result Backend URL"""
        redis_url = self.get_redis_url
        if redis_url:
            return redis_url
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @model_validator(mode="after")
    def validate_serverless_config(self):
        """
        Validate configuration for serverless (Vercel) deployment.
        
        Warnings are logged for missing critical services on Vercel,
        but deployment is not blocked (graceful degradation).
        """
        if self.VERCEL == "1":
            # Check database configuration
            if not any([self.NEON_DATABASE_URL, self.DATABASE_URL, self.POSTGRES_URL]):
                logger.warning(
                    "Vercel deployment detected but no DATABASE_URL configured. "
                    "Using local PostgreSQL settings (may fail in serverless)."
                )

            # Check Redis configuration
            if not any([self.UPSTASH_REDIS_URL, self.KV_URL, self.REDIS_URL]):
                logger.warning(
                    "Vercel deployment detected but no Redis URL configured. "
                    "Using local Redis settings (may fail in serverless)."
                )

        return self

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables not defined in Settings


settings = Settings()
