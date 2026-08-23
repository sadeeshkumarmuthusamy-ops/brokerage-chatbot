from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str | None:
    start_path = Path(__file__).resolve()
    for directory in [start_path.parent, *start_path.parents]:
        candidate = directory / ".env"
        if candidate.exists():
            return str(candidate)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App Settings
    PROJECT_NAME: str = "brokerage-chatbot-api"

    GROQ_LLM_PROVIDER: str = Field(default="groq")
    GROQ_LLM_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_LLM_TEMPERATURE: float = Field(default=0.0)
    OPENAI_LLM_PROVIDER: str = Field(default="openai")
    OPENAI_LLM_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_LLM_TEMPERATURE: float = Field(default=0.0)

    # API Keys
    GROQ_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    TAVILY_API_KEY: str | None = None
    CHROMA_DB_PATH: str | None = None
    PDF_PATH: str | None = None

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    CHROMA_DB_PATH_LOCAL : str | None = None

    API_URL_PATH : str | None = None

# Global settings instance
settings = Settings()


def reload_settings() -> Settings:
    global settings
    settings = Settings()
    return settings