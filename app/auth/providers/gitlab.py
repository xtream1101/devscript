from fastapi_sso.sso.gitlab import GitlabSSO

from app.settings import settings

sso = GitlabSSO(
    settings.GITLAB_CLIENT_ID,
    settings.GITLAB_CLIENT_SECRET,
    f"{settings.HOST}/auth/gitlab/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.GITLAB_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.GITLAB_CLIENT_ID and settings.GITLAB_CLIENT_SECRET)
sso.button_text = "Login with Gitlab"
