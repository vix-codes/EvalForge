from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "EvalForge"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(min_length=32)
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://evalforge:evalforge@localhost:5432/evalforge"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CELERY_URL: str = "redis://localhost:6379/1"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "phi4"
    OLLAMA_TIMEOUT: int = 300
    OLLAMA_MAX_RETRIES: int = 3
    OLLAMA_MAX_TOKENS: int = 220
    OLLAMA_NUM_CTX: int = 4096
    OLLAMA_NUM_BATCH: int = 128
    # Reduced params used on OOM (HTTP 500) retry
    OLLAMA_RETRY_NUM_PREDICT: int = 128
    OLLAMA_RETRY_NUM_CTX: int = 2048
    # Max input characters per prompt before truncation (prevents OOM on long questions)
    OLLAMA_MAX_PROMPT_CHARS: int = 1200

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_JUDGE_ENABLED: bool = False

    # Scoring
    SIMILARITY_THRESHOLD: float = 0.7
    KEYWORD_COVERAGE_THRESHOLD: float = 0.5
    HALLUCINATION_SIMILARITY_THRESHOLD: float = 0.4
    HALLUCINATION_KEYWORD_THRESHOLD: float = 0.3

    # GitHub Webhooks
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_TOKEN: str = ""

    # RAG Settings
    DOCS_DIR: str = "docs"
    CHROMA_PERSIST_DIR: str = "backend/data/chroma_db"
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 3
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # Quality Gates
    MAX_HALLUCINATION_RATE: float = 0.15
    MAX_P95_LATENCY_MS: float = 10000.0
    MIN_PASS_RATE: float = 0.80

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def allowed_origins_list(self) -> list[str]:
        value = self.ALLOWED_ORIGINS.strip()
        if not value:
            return []
        if value.startswith("["):
            import json

            parsed = json.loads(value)
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
