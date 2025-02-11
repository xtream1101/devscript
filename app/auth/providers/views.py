import base64
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.auth.models import Invitation, User
from app.common.db import get_async_session
from app.common.exceptions import (
    AuthBannedError,
    AuthDuplicateError,
    UserNotVerifiedError,
    ValidationError,
)
from app.common.utils import flash
from app.settings import settings

from ..serializers import TokenDataSerializer, UserSignUpSerializer
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
async def sso_login(provider: str, request: Request):
    provider = providers.get(provider.lower())
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    # Get invitation token from query params if it exists
    token = request.query_params.get("token")

    # Create state parameter with token if it exists
    state = None
    if token:
        state_data = {"token": token}
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    async with provider:
        # Get the login redirect URL with our state
        response = await provider.get_login_redirect(state=state)
        return response


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

    # If connecting provider to existing account, redirect to account settings
    redirect_url = "auth.login" if not current_user else "auth.account_settings"
    try:
        async with provider:
            sso_user = await provider.verify_and_process(request)

        email = sso_user.email
        if email is None:
            flash(request, "No email provided by the provider", "error")
            return RedirectResponse(
                url=request.url_for(redirect_url), status_code=status.HTTP_303_SEE_OTHER
            )

        found_user = await get_user(session, email, sso_user.provider)
        if current_user and found_user and found_user.id != current_user.id:
            raise AuthDuplicateError(
                f"This {provider_name} account is already connected to a different user"
            )

        if not found_user:
            # Check if this would be the first user
            query = select(User)
            result = await session.execute(query)
            is_first_user = result.first() is None

            # Block SSO registration if disabled (except for first user or valid invitation)
            if not current_user and settings.DISABLE_REGISTRATION and not is_first_user:
                # Check for invitation token in state parameter
                state = request.query_params.get("state")
                token = None
                if state:
                    try:
                        state_data = json.loads(
                            base64.urlsafe_b64decode(state).decode()
                        )
                        token = state_data.get("token")
                    except:
                        logger.exception("Error decoding state parameter")
                if token:
                    # Check invitation token
                    query = select(Invitation).filter(
                        Invitation.token == token,
                        Invitation.expires_at > datetime.now(timezone.utc),
                        Invitation.used_at.is_(None),
                    )
                    result = await session.execute(query)
                    invitation = result.scalar_one_or_none()

                    if not invitation or invitation.email.lower() != email.lower():
                        flash(
                            request,
                            "Invalid invitation or email does not match invitation",
                            "error",
                        )
                        return RedirectResponse(
                            url=request.url_for(redirect_url),
                            status_code=status.HTTP_303_SEE_OTHER,
                        )

                    # Mark invitation as used
                    invitation.used_at = datetime.now(timezone.utc)
                    await session.commit()
                else:
                    flash(request, "Registration is currently disabled", "error")
                    return RedirectResponse(
                        url=request.url_for(redirect_url),
                        status_code=status.HTTP_303_SEE_OTHER,
                    )

            user_stored = await add_user(
                session,
                UserSignUpSerializer(email=email),
                sso_user.provider,
                sso_user.display_name,
                is_verified=provider.is_trused_provider,
                existing_user=current_user,
            )
            if (
                not user_stored.is_admin
                and not provider.is_trused_provider
                and not current_user
            ):
                # This is a new user signup
                flash(
                    request,
                    "Registration successful! Please check your email to verify your account.",
                    "success",
                )
                return RedirectResponse(
                    url=request.url_for(redirect_url),
                    status_code=status.HTTP_303_SEE_OTHER,
                )

        # Will make sure the provider is verified
        # I know this is an extra call, but this way the check is always the same
        user_stored = await authenticate_user(
            session, email=email, provider=sso_user.provider
        )

        if current_user:
            flash(request, f"Connected {provider_name.title()} account", "success")

        access_token = await create_token(
            TokenDataSerializer(
                user_id=user_stored.id,
                email=email,  # Make sure to use the email linked to the provider, not the users primary email as it may be different
                provider_name=provider_name,
                token_type="access",
            )
        )
        response = RedirectResponse(
            url=request.url_for(redirect_url), status_code=status.HTTP_303_SEE_OTHER
        )
        response.set_cookie(settings.COOKIE_NAME, access_token)

        return response

    except AuthDuplicateError as e:
        # Can happen in the add_user function
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for(redirect_url),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except UserNotVerifiedError:
        if current_user:
            # Catch this case here so we can stay on the account settings page
            flash(
                request,
                "This account is not verified. Please check your email for the verification link.",
                "error",
            )
            return RedirectResponse(
                url=request.url_for(redirect_url),
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Is caught and handled in the global app exception handler
        raise

    except AuthBannedError:
        # Let the global app exception handler handle this
        raise

    except ValidationError as e:
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for("auth.login"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception:
        logger.exception("Error connecting provider")
        flash(request, f"Error connecting {provider_name}", "error")
        return RedirectResponse(
            url=request.url_for(redirect_url), status_code=status.HTTP_303_SEE_OTHER
        )
