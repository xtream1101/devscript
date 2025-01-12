from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    DEBUG: bool = False
    APP_NAME: str = "Snippet Manager"
    HOST: str = "http://localhost:8000"

    # Database Settings
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "postgres"

    # Authentication Settings
    SECRET_KEY: str = "SECRET"  # Should be overridden in production
    VALIDATION_LINK_EXPIRATION: int = 60 * 15  # (sec) 15 minutes

    # Cookie Settings
    COOKIE_NAME: str = "snippetmanagerauth"
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 30  # (sec) 30 days

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

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"


# Create settings instance
settings = Settings()
