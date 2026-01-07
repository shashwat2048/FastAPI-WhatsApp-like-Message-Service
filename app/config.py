"""
12-factor app configuration using environment variables.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database URL (e.g., sqlite:////data/app.db for Docker, sqlite:///./data/app.db for local)
    DATABASE_URL: str = "sqlite:///./data/app.db"
    
    # Webhook secret (no default value, but optional to prevent import crash)
    WEBHOOK_SECRET: Optional[str] = None
    
    # Logging level
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()

