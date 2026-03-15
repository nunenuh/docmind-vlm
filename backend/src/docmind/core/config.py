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
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="")

    # Database (Supabase Postgres via SQLAlchemy)
    DATABASE_URL: str = Field(default="postgresql+asyncpg://localhost:5432/docmind")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Data
    DATA_DIR: str = Field(default="data")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS_STR.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
