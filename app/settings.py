from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application Settings
    DEBUG: bool = False
    APP_NAME: str = "Snippet Manager"

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Authentication Settings
    JWT_SECRET: str = "SECRET"  # Should be overridden in production
    JWT_LIFETIME_SECONDS: int = 3600

    # Cookie Settings
    COOKIE_NAME: str = "snippetmanagerauth"
    COOKIE_MAX_AGE: int = 3600

    # Email Settings (for future use)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
