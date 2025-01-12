import oauthlib.oauth2.rfc6749.errors
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from loguru import logger
from starlette.requests import Request

from app.common.db import async_session_maker
from app.common.exceptions import DuplicateError, GenericException
from app.settings import settings

from ..schemas import TokenData, UserSignUp
from ..utils import (
    add_user,
    authenticate_user,
    create_token,
    get_user,
    optional_current_user,
)
from .facebook import sso as facebook_sso
from .generic_oidc import sso as generic_oidc_sso
from .github import sso as github_sso
from .gitlab import sso as gitlab_sso
from .google import sso as google_sso
from .linkedin import sso as linkedin_sso
from .microsoft import sso as microsoft_sso
from .spotify import sso as spotify_sso
from .xtwitter import sso as twitter_sso

router = APIRouter()

supported_providers = (
    facebook_sso,
    generic_oidc_sso,
    github_sso,
    gitlab_sso,
    google_sso,
    linkedin_sso,
    microsoft_sso,
    spotify_sso,
    twitter_sso,
)
providers = {}
for provider in supported_providers:
    if provider.is_enabled:
        providers[provider.provider] = provider


@router.get("/{provider}/login", name="auth.providers.login", tags=["SSO"])
async def sso_login(provider: str):
    provider = providers.get(provider.lower())
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )
    async with provider:
        return await provider.get_login_redirect()


@router.get("/{provider}/connect", name="auth.providers.connect", tags=["SSO"])
async def sso_connect(provider: str):
    """Start OAuth flow for connecting to existing account"""
    provider = providers.get(provider.lower())
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )
    async with provider:
        return await provider.get_login_redirect()


@router.get("/{provider_name}/callback", name="auth.providers.callback", tags=["SSO"])
async def sso_callback(
    provider_name: str, request: Request, current_user=Depends(optional_current_user)
):
    """Process login response and return user info"""
    provider = providers.get(provider_name.lower())
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    # If connecting provider to existing account, redirect to profile
    redirect_url = "/" if not current_user else "/profile"
    try:
        async with provider:
            sso_user = await provider.verify_and_process(request)

        async with async_session_maker() as session:
            email = sso_user.email
            if email is None:
                raise GenericException(detail="No email provided by the provider")

            found_user = await get_user(session, email, sso_user.provider)

            if not found_user:
                user_stored = await add_user(
                    session,
                    UserSignUp(email=email),
                    sso_user.provider,
                    sso_user.display_name,
                    is_verified=provider.is_trused_provider,
                    existing_user=current_user,
                )

            # Will make sure the provider is verified
            # I know this is an extra call, but this way the check is always the same
            user_stored = await authenticate_user(
                session, email=email, provider=sso_user.provider
            )

        access_token = await create_token(
            TokenData(
                user_id=user_stored.id,
                email=email,  # Make sure to use the email linked to the provider, not the users primary email as it may be different
                provider_name=provider_name,
                token_type="access",
            )
        )
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        response.set_cookie(settings.COOKIE_NAME, access_token)

        return response

    except DuplicateError as e:
        return RedirectResponse(
            url=f"{redirect_url}?error={str(e)}", status_code=status.HTTP_302_FOUND
        )

    except oauthlib.oauth2.rfc6749.errors.CustomOAuth2Error:
        raise GenericException(detail="The code passed is incorrect or expired")

    except ValueError:
        logger.exception("Error connecting provider")
        raise GenericException(detail="An unexpected error occurred")
