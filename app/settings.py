from pathlib import Path
from typing import Literal, Optional

import toml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    ENV: Literal["dev", "staging", "prod"] = "dev"
    HOST: str = "http://localhost:8000"
    SENTRY_DSN: Optional[str] = None

    # Docs Settings
    DOCS_HOST: str = "http://localhost:8080"

    # Database Settings
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "postgres"

    # Authentication Settings
    SECRET_KEY: str = "SECRET"  # Should be overridden in production
    VALIDATION_LINK_EXPIRATION: int = 60 * 60  # (sec) 1 hour
    PASSWORD_RESET_LINK_EXPIRATION: int = 60 * 60  # (sec) 1 hour

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

    DEFAULT_CODE_THEME: str = "night-owl"

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

    @property
    def version(self) -> str:
        DEFAULT_VERSION = "0.0.0"
        version = DEFAULT_VERSION

        pyproject_toml_file = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
            data = toml.load(pyproject_toml_file)
            version = data.get("project", {}).get("version", DEFAULT_VERSION)

        return version


# Create settings instance
settings = Settings()
