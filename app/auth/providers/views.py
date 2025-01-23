from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.common.db import get_async_session
from app.common.exceptions import AuthDuplicateError, UserNotVerifiedError
from app.common.utils import flash
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
from .twitter import sso as twitter_sso

router = APIRouter(include_in_schema=False)

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
    provider_name: str,
    request: Request,
    current_user=Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Process login response and return user info"""
    provider = providers.get(provider_name.lower())
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    # If connecting provider to existing account, redirect to profile
    redirect_url = "auth.login" if not current_user else "auth.profile"
    try:
        async with provider:
            sso_user = await provider.verify_and_process(request)

        email = sso_user.email
        if email is None:
            flash(request, "No email provided by the provider", "error")
            return RedirectResponse(
                url=request.url_for(redirect_url), status_code=status.HTTP_302_FOUND
            )

        found_user = await get_user(session, email, sso_user.provider)
        if current_user and found_user and found_user.id != current_user.id:
            raise AuthDuplicateError(
                f"This {provider_name} account is already connected to a different user"
            )

        if not found_user:
            user_stored = await add_user(
                session,
                UserSignUp(email=email),
                sso_user.provider,
                sso_user.display_name,
                is_verified=provider.is_trused_provider,
                existing_user=current_user,
            )
            if not provider.is_trused_provider and not current_user:
                # This is a new user signup
                flash(
                    request,
                    "Registration successful! Please check your email to verify your account.",
                    "success",
                )
                return RedirectResponse(
                    url=request.url_for(redirect_url),
                    status_code=status.HTTP_302_FOUND,
                )

        # Will make sure the provider is verified
        # I know this is an extra call, but this way the check is always the same
        user_stored = await authenticate_user(
            session, email=email, provider=sso_user.provider
        )

        if current_user:
            flash(request, f"Connected {provider_name.title()} account", "success")

        access_token = await create_token(
            TokenData(
                user_id=user_stored.id,
                email=email,  # Make sure to use the email linked to the provider, not the users primary email as it may be different
                provider_name=provider_name,
                token_type="access",
            )
        )
        response = RedirectResponse(
            url=request.url_for(redirect_url), status_code=status.HTTP_302_FOUND
        )
        response.set_cookie(settings.COOKIE_NAME, access_token)

        return response

    except AuthDuplicateError as e:
        # Can happen in the add_user function
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for(redirect_url),
            status_code=status.HTTP_302_FOUND,
        )

    except UserNotVerifiedError:
        if current_user:
            # Catch this case here so we can stay on the profile page
            flash(
                request,
                "This account is not verified. Please check your email for the verification link.",
                "error",
            )
            return RedirectResponse(
                url=request.url_for(redirect_url),
                status_code=status.HTTP_302_FOUND,
            )

        # Is caught and handled in the global app exception handler
        raise

    except Exception:
        logger.exception("Error connecting provider")
        flash(request, f"Error connecting {provider_name}", "error")
        return RedirectResponse(
            url=request.url_for(redirect_url), status_code=status.HTTP_302_FOUND
        )
