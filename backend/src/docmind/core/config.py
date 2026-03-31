from functools import lru_cache

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    APP_NAME: str = Field(default="DocMind-VLM")
    APP_DESCRIPTION: str = Field(
        default="Intelligent document extraction and chat"
        " platform powered by Vision Language Models"
    )
    APP_VERSION: str = Field(default="0.1.0")
    APP_ENVIRONMENT: str = Field(default="development")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    APP_DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    ALLOWED_ORIGINS_STR: str = Field(
        default="http://localhost:5173,http://localhost:3000"
    )

    # VLM Provider
    VLM_PROVIDER: str = Field(default="dashscope")

    # DashScope
    DASHSCOPE_API_KEY: str = Field(default="")
    DASHSCOPE_MODEL: str = Field(default="qwen-vl-max")
    DASHSCOPE_BASE_URL: str = Field(
        default="https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )
    DASHSCOPE_MAX_RETRIES: int = Field(default=3)
    DASHSCOPE_RETRY_DELAY: float = Field(default=2.0)
    DASHSCOPE_TIMEOUT: float = Field(default=120.0)

    # OpenAI
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o")

    # Google
    GOOGLE_API_KEY: str = Field(default="")
    GOOGLE_MODEL: str = Field(default="gemini-2.0-flash")

    # Ollama
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llava")

    # Supabase (Auth + Storage)
    SUPABASE_URL: str = Field(default="")
    SUPABASE_PUBLISHABLE_KEY: str = Field(default="")
    SUPABASE_SECRET_KEY: str = Field(default="")
    JWT_SECRET: str = Field(default="", description="HMAC secret for local Supabase JWT verification")

    # Database (Supabase Postgres via SQLAlchemy)
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="")
    DB_NAME: str = Field(default="postgres")
    DB_CONNECT_TIMEOUT: int = Field(default=60)
    DB_MAX_RETRIES: int = Field(default=3)
    DB_RETRY_DELAY: float = Field(default=1.0)
    DB_ECHO: bool = Field(default=False)

    @property
    def database_url(self) -> str:
        """Build async database URL from individual components."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Storage
    STORAGE_BUCKET: str = Field(default="documents")

    # Data
    DATA_DIR: str = Field(default="data")

    # Upload limits
    MAX_UPLOAD_SIZE: int = Field(default=20_971_520)  # 20MB
    MAX_FILENAME_LENGTH: int = Field(default=255)

    # CV preprocessing
    CV_MAX_DIMENSION: int = Field(default=4096)
    CV_TARGET_DPI: int = Field(default=300)

    # Pipeline confidence
    CONFIDENCE_VLM_WEIGHT: float = Field(default=0.7)
    CONFIDENCE_CV_WEIGHT: float = Field(default=0.3)
    CONFIDENCE_LOW_THRESHOLD: float = Field(default=0.5)

    # RAG
    EMBEDDING_PROVIDER: str = Field(default="dashscope")
    EMBEDDING_MODEL: str = Field(default="text-embedding-v4")
    EMBEDDING_DIMENSIONS: int = Field(default=1024)
    RAG_CHUNK_SIZE: int = Field(default=1200)
    RAG_CHUNK_OVERLAP: int = Field(default=200)
    RAG_TOP_K: int = Field(default=5)
    RAG_RETRIEVAL_K: int = Field(default=20)
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.1)
    RAG_BM25_WEIGHT: float = Field(default=0.4)
    RAG_VECTOR_WEIGHT: float = Field(default=0.6)
    RAG_BM25_LANGUAGE: str = Field(default="simple")
    RAG_ENABLE_QUERY_REWRITE: bool = Field(default=True)
    RAG_MAX_EMBEDDING_TOKENS: int = Field(default=7500)
    RAG_PAGE_CHUNK_THRESHOLD: int = Field(default=1500)

    # Chat pipeline
    CHAT_MAX_PAGE_IMAGES: int = Field(default=4)
    CHAT_MAX_HISTORY: int = Field(default=6)
    CHAT_MAX_REQUERY_FIELDS: int = Field(default=3)
    CHAT_LOW_CONFIDENCE: float = Field(default=0.6)
    CHAT_HEARTBEAT_TIMEOUT: float = Field(default=120.0)

    # SSE
    SSE_HEARTBEAT_TIMEOUT: float = Field(default=30.0)

    # Embedding
    EMBEDDING_TIMEOUT: float = Field(default=60.0)

    # DashScope VLM generation parameters
    DASHSCOPE_MAX_TOKENS: int = Field(default=4096)
    DASHSCOPE_TEMPERATURE: float = Field(default=0.1)

    # Streaming + Thinking
    ENABLE_THINKING: bool = Field(default=True)
    THINKING_BUDGET: int = Field(default=10000)

    # CV Processing
    CV_DESKEW_THRESHOLD: float = Field(default=2.0)
    CV_QUALITY_GRID_SIZE: int = Field(default=4)

    # Confidence thresholds
    CONFIDENCE_HIGH_THRESHOLD: float = Field(default=0.8)
    CONFIDENCE_MEDIUM_THRESHOLD: float = Field(default=0.5)

    # Colors (confidence overlay)
    COLOR_CONFIDENCE_HIGH: str = Field(default="#22c55e")
    COLOR_CONFIDENCE_MEDIUM: str = Field(default="#f59e0b")
    COLOR_CONFIDENCE_LOW: str = Field(default="#ef4444")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS_STR.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
