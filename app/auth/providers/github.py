from fastapi_sso.sso.github import GithubSSO

from app.settings import settings

sso = GithubSSO(
    settings.GITHUB_CLIENT_ID,
    settings.GITHUB_CLIENT_SECRET,
    f"{settings.HOST}/auth/github/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.GITHUB_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)
