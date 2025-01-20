from fastapi_sso.sso.facebook import FacebookSSO

from app.settings import settings

sso = FacebookSSO(
    settings.FACEBOOK_CLIENT_ID,
    settings.FACEBOOK_CLIENT_SECRET,
    f"{settings.HOST}/auth/facebook/callback",  # Cant use url_for heren as the routers have not been added yet
)

sso.is_trused_provider = settings.FACEBOOK_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET)
sso.button_text = "Login with Facebook"
