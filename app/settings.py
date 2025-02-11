from typing import List, Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    VERSION: str = "0.1.0"
    ENV: Literal["dev", "staging", "prod"] = "dev"
    HOST: str = "http://localhost:8000"
    SENTRY_DSN: Optional[str] = None
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://localhost:8080",
    ]

    # Docs Settings
    DOCS_HOST: str = "http://localhost:8080"

    # Support Email
    SUPPORT_EMAIL: str = "support@example.com"

    # Syntax Highlighting
    DEFAULT_CODE_THEME_LIGHT: str = "atom-one-light"
    DEFAULT_CODE_THEME_DARK: str = "atom-one-dark"

    # Database Settings
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "postgres"

    # Authentication Settings
    SECRET_KEY: str = "SECRET"  # Should be overridden in production
    DISABLE_REGISTRATION: bool = False  # When True, prevents new user registration
    VALIDATION_LINK_EXPIRATION: int = 60 * 60  # (sec) 1 hour
    PASSWORD_RESET_LINK_EXPIRATION: int = 60 * 60  # (sec) 1 hour

    # Cookie Settings
    COOKIE_NAME: str = "snippetmanagerauth"
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 30  # (sec) 30 days

    # Plausible Analytics
    PLAUSIBLE_SITE_NAME: Optional[str] = None
    PLAUSIBLE_SCRIPT_URL: Optional[str] = None

    # Email Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_STARTTLS: bool = False
    SMTP_SSL: bool = False
    SMTP_FROM: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = None
    # Enables debug output for email
    SMTP_DEBUG: bool = False
    # Disables sending of emails and prints locally in terminal for local dev
    SMTP_LOCAL_DEV: bool = False

    # Supported SSO Services
    FACEBOOK_CLIENT_ID: Optional[str] = None
    FACEBOOK_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_AUTO_VERIFY_EMAIL: bool = True

    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_AUTO_VERIFY_EMAIL: bool = True

    GITLAB_CLIENT_ID: Optional[str] = None
    GITLAB_CLIENT_SECRET: Optional[str] = None
    GITLAB_AUTO_VERIFY_EMAIL: bool = True

    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_AUTO_VERIFY_EMAIL: bool = True

    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_AUTO_VERIFY_EMAIL: bool = True

    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_AUTO_VERIFY_EMAIL: bool = True

    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None
    SPOTIFY_AUTO_VERIFY_EMAIL: bool = True

    XTWITTER_CLIENT_ID: Optional[str] = None
    XTWITTER_CLIENT_SECRET: Optional[str] = None
    XTWITTER_AUTO_VERIFY_EMAIL: bool = True

    # Callback for custom provider will be /auth/{GENERIC_OIDC_NAME}/callback
    GENERIC_OIDC_DISCOVERY_URL: Optional[str] = None
    GENERIC_OIDC_NAME: Optional[str] = None
    GENERIC_OIDC_CLIENT_ID: Optional[str] = None
    GENERIC_OIDC_CLIENT_SECRET: Optional[str] = None
    GENERIC_OIDC_ALLOW_INSECURE_HTTP: bool = False
    GENERIC_OIDC_AUTO_VERIFY_EMAIL: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"


# Create settings instance
settings = Settings()
