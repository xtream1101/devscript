from typing import ClassVar, Optional

import httpx
from fastapi_sso.sso.base import DiscoveryDocument, OpenID, SSOBase, SSOLoginError

from app.common.utils import get_key_from_options
from app.settings import settings


class GenericSSO(SSOBase):
    """Class providing login via Generic OIDC Auth."""

    discovery_url = settings.GENERIC_OIDC_DISCOVERY_URL
    provider = settings.GENERIC_OIDC_NAME
    scope: ClassVar = ["openid", "email", "profile"]

    async def openid_from_response(
        self, response: dict, session: Optional["httpx.AsyncClient"] = None
    ) -> OpenID:
        """Return OpenID from user information provided by the provider"""
        if (
            response.get("email_verified")
            or settings.GENERIC_OIDC_AUTO_VERIFY_EMAIL is True
        ):
            return OpenID(
                # Some providers may send different fields, so we need to check for multiple fields as needed
                email=response.get("email"),
                provider=self.provider,
                id=response.get("sub"),
                first_name=response.get("given_name"),
                last_name=response.get("family_name"),
                display_name=get_key_from_options(
                    response, ["preferred_username", "nickname", "name"]
                ),
                picture=response.get("picture"),
            )
        raise SSOLoginError(
            401,
            f"User {response.get('email')} is not verified with {settings.GENERIC_OIDC_NAME}",
        )

    async def get_discovery_document(self) -> DiscoveryDocument:
        """Get document containing handy urls."""
        async with httpx.AsyncClient() as session:
            response = await session.get(self.discovery_url)
            content = response.json()
            return content


provider_name = f"{settings.GENERIC_OIDC_NAME}"
sso = GenericSSO(
    settings.GENERIC_OIDC_CLIENT_ID,
    settings.GENERIC_OIDC_CLIENT_SECRET,
    redirect_uri=f"{settings.HOST}/auth/{provider_name}/callback",  # Cant use url_for here as the routers have not been added yet
    allow_insecure_http=settings.GENERIC_OIDC_ALLOW_INSECURE_HTTP,
)

sso.is_trused_provider = settings.GENERIC_OIDC_AUTO_VERIFY_EMAIL
sso.is_enabled = bool(
    settings.GENERIC_OIDC_CLIENT_ID and settings.GENERIC_OIDC_CLIENT_SECRET
)
