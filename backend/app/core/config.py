from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # =====================================================
    # Application
    # =====================================================

    APP_NAME: str = "EnterpriseIQ"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # =====================================================
    # Database
    # =====================================================

    DATABASE_URL: str

    # =====================================================
    # JWT
    # =====================================================

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # =====================================================
    # Qdrant
    # =====================================================

    QDRANT_URL: str = "http://localhost:6333"

    QDRANT_COLLECTION: str = (
        "enterpriseiq_documents"
    )

    # =====================================================
    # Embeddings
    # =====================================================

    EMBEDDING_MODEL: str = (
        "all-MiniLM-L6-v2"
    )

    # =====================================================
    # Groq
    # =====================================================

    GROQ_API_KEY: str

    GROQ_MODEL: str = (
        "llama-3.3-70b-versatile"
    )

    # =====================================================
    # Environment Configuration
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()