from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings
    """

    PROJECT_NAME: str = "Biz-Retriever Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 보안 강화: 15분 (Refresh Token으로 재발급)
    FRONTEND_URL: str = "http://localhost:8081"

    # Environment
    DEBUG: bool = False  # Set to False in production
    SQL_ECHO: bool = False  # SQL query logging (disable in production)

    # Database - Railway provides DATABASE_URL directly
    DATABASE_URL: str | None = None
    POSTGRES_SERVER: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_PORT: str | None = None

    # Redis - Railway provides REDIS_URL directly
    REDIS_URL: str | None = None
    REDIS_HOST: str | None = None
    REDIS_PORT: str | None = None
    REDIS_PASSWORD: str | None = None

    # OpenAI (optional)
    OPENAI_API_KEY: str | None = None

    # Google Gemini API (AI analysis - recommended)
    GEMINI_API_KEY: str | None = None

    # Phase 1: G2B API (나라장터) - 데이터셋 개방표준 서비스
    G2B_API_KEY: str | None = None
    G2B_API_ENDPOINT: str = "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo"
    G2B_RESULT_API_ENDPOINT: str = "https://apis.data.go.kr/1230000/OpengResultService/getOpengResultInfoListSet"

    # Phase 1: Slack Notification
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_CHANNEL: str = "#입찰-알림"

    # Phase 8: Email Notification (SendGrid)
    SENDGRID_API_KEY: str | None = None
    SENDGRID_FROM_EMAIL: str = "noreply@biz-retriever.com"
    SENDGRID_FROM_NAME: str = "Biz-Retriever"

    # Phase 3: Payment Gateway (Tosspayments)
    TOSSPAYMENTS_SECRET_KEY: str | None = None
    TOSSPAYMENTS_CLIENT_KEY: str | None = None
    TOSSPAYMENTS_WEBHOOK_SECRET: str | None = None  # 웹훅 HMAC 검증용

    # Railway deployment
    RAILWAY_PUBLIC_DOMAIN: str | None = None
    ALLOWED_HOSTS: str | None = None

    # CORS Settings
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "https://biz-retriever.vercel.app",  # Vercel Production
        "https://biz-retriever-doublesilvers-projects.vercel.app",  # Vercel Auto Domain
        "https://biz-retriever-git-master-doublesilvers-projects.vercel.app",  # Vercel Branch
    ]
    PRODUCTION_DOMAIN: str | None = None

    @model_validator(mode="before")
    @classmethod
    def assemble_urls(cls, values: dict) -> dict:
        """Assemble DATABASE_URL and REDIS_URL from parts if not provided directly."""
        # DATABASE_URL assembly
        db_url = values.get("DATABASE_URL")
        if db_url:
            # Railway provides postgres:// which SQLAlchemy doesn't support
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            values["DATABASE_URL"] = db_url
        else:
            # Fall back to individual POSTGRES_* variables (local development)
            server = values.get("POSTGRES_SERVER")
            user = values.get("POSTGRES_USER")
            password = values.get("POSTGRES_PASSWORD")
            db = values.get("POSTGRES_DB")
            port = values.get("POSTGRES_PORT")
            if all([server, user, password, db, port]):
                values["DATABASE_URL"] = f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

        # REDIS_URL assembly
        redis_url = values.get("REDIS_URL")
        if not redis_url:
            host = values.get("REDIS_HOST")
            port = values.get("REDIS_PORT")
            redis_password = values.get("REDIS_PASSWORD")
            if host and port:
                if redis_password:
                    values["REDIS_URL"] = f"redis://:{redis_password}@{host}:{port}"
                else:
                    values["REDIS_URL"] = f"redis://{host}:{port}"

        return values

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Alias for DATABASE_URL (backward compatibility)"""
        return self.DATABASE_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
