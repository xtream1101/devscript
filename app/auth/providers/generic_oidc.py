from fastapi_sso.sso.generic import create_provider

from app.settings import settings

discovery = {
    "authorization_endpoint": settings.GENERIC_OIDC_AUTHORIZATION_ENDPOINT,
    "token_endpoint": settings.GENERIC_OIDC_TOKEN_ENDPOINT,
    "userinfo_endpoint": settings.GENERIC_OIDC_USERINFO_ENDPOINT,
}
provider_name = f"{settings.GENERIC_OIDC_NAME}"
SSOProvider = create_provider(name=provider_name, discovery_document=discovery)
sso = SSOProvider(
    client_id=settings.GENERIC_OIDC_CLIENT_ID,
    client_secret=settings.GENERIC_OIDC_CLIENT_SECRET,
    redirect_uri=f"{settings.HOST}/auth/{provider_name}/callback",  # Cant use url_for here as the routers have not been added yet
    allow_insecure_http=settings.GENERIC_OIDC_ALLOW_INSECURE_HTTP,
)

sso.is_trused_provider = settings.GENERIC_OIDC_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(
    settings.GENERIC_OIDC_CLIENT_ID and settings.GENERIC_OIDC_CLIENT_SECRET
)
sso.button_text = f"Login with { sso.provider.title() }"
sso.icon = ""
