from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    DEBUG: bool = False
    APP_NAME: str = "Snippet Manager"
    HOST: str = "http://localhost:8000"

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

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
    SMTP_PASSWORD: Optional[str] = "password"
    SMTP_STARTTLS: bool = False
    SMTP_SSL: bool = False
    SMTP_FROM: Optional[str] = "foobar@example.com"
    SMTP_FROM_NAME: Optional[str] = "Example"
    # Enables debug put for email
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

    GENERIC_OIDC_AUTHORIZATION_ENDPOINT: Optional[str] = None
    GENERIC_OIDC_TOKEN_ENDPOINT: Optional[str] = None
    GENERIC_OIDC_USERINFO_ENDPOINT: Optional[str] = None
    GENERIC_OIDC_NAME: Optional[str] = None
    GENERIC_OIDC_CLIENT_ID: Optional[str] = None
    GENERIC_OIDC_CLIENT_SECRET: Optional[str] = None
    GENERIC_OIDC_ALLOW_INSECURE_HTTP: bool = False
    GENERIC_OIDC_AUTO_VERIFY_EMAIL: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
