from fastapi_sso.sso.twitter import TwitterSSO

from app.settings import settings

sso = TwitterSSO(
    settings.XTWITTER_CLIENT_ID,
    settings.XTWITTER_CLIENT_SECRET,
    f"{settings.HOST}/auth/twitter/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.XTWITTER_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.XTWITTER_CLIENT_ID and settings.XTWITTER_CLIENT_SECRET)
