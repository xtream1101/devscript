from fastapi_sso.sso.microsoft import MicrosoftSSO

from app.settings import settings

sso = MicrosoftSSO(
    settings.MICROSOFT_CLIENT_ID,
    settings.MICROSOFT_CLIENT_SECRET,
    f"{settings.HOST}/auth/microsoft/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.MICROSOFT_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET)
sso.button_text = "Login with Microsoft"
