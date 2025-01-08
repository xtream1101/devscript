from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    DEBUG: bool = False
    APP_NAME: str = "Snippet Manager"
    HOST: str = "http://localhost:8000"

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Authentication Settings
    JWT_SECRET: str = "SECRET"  # Should be overridden in production
    JWT_LIFETIME_SECONDS: int = 3600

    # Cookie Settings
    COOKIE_NAME: str = "snippetmanagerauth"
    COOKIE_MAX_AGE: int = 3600

    # Email Settings
    SMTP_HOST: Optional[str] = "example.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = "foobar@example.com"
    SMTP_PASSWORD: Optional[str] = None
    SMTP_STARTTLS: bool = False
    SMTP_SSL: bool = False
    SMTP_FROM: Optional[str] = "foobar@example.com"
    SMTP_FROM_NAME: Optional[str] = "Example"
    # Enables debug put for email
    SMTP_DEBUG: bool = False
    # Disables sending of emails and prints locally in terminal for local dev
    SMTP_LOCAL_DEV: bool = False

    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
