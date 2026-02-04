"""Application configuration"""
from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment"""
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # API Configuration
    API_V1_STR: str = "/api/v1"
    APP_NAME: str = "Mobox API"
    ENVIRONMENT: Environment = Environment.LOCAL
    LOG_LEVEL: str = "INFO"
    
    # Server Configuration
    PORT: int = 8080
    HOST: str = "0.0.0.0"

    # PostgreSQL Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mobox"
    POSTGRES_USER: str = "mobox"
    POSTGRES_PASSWORD: str = "mobox"
    
    # Sandbox backend: "subprocess" (default) or "modal"
    SANDBOX_BACKEND: str = "subprocess"

    # Modal Configuration (for sandbox execution)
    MODAL_TOKEN_ID: str = ""
    MODAL_TOKEN_SECRET: str = ""
    
    # Anthropic API key
    ANTHROPIC_API_KEY: str = ""

    # OpenAI API key
    OPENAI_API_KEY: str = ""

    # TAVILY API key
    TAVILY_API_KEY: str = ""


settings = Settings()
