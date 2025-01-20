from fastapi_sso.sso.linkedin import LinkedInSSO

from app.settings import settings

sso = LinkedInSSO(
    settings.LINKEDIN_CLIENT_ID,
    settings.LINKEDIN_CLIENT_SECRET,
    f"{settings.HOST}/auth/linkedin/callback",  # Cant use url_for here as the routers have not been added yet
)

sso.is_trused_provider = settings.LINKEDIN_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET)
sso.button_text = "Login with Linkedin"
