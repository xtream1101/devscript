from fastapi_sso.sso.google import GoogleSSO

from app.settings import settings

sso = GoogleSSO(
    settings.GOOGLE_CLIENT_ID,
    settings.GOOGLE_CLIENT_SECRET,
    f"{settings.HOST}/auth/google/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.GOOGLE_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
