import oauthlib.oauth2.rfc6749.errors
from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.github import GithubSSO
from loguru import logger
from starlette.requests import Request

from app.common.db import async_session_maker
from app.common.exceptions import DuplicateError, GenericException
from app.settings import settings

from ..schemas import UserSignUp
from ..utils import (
    add_user,
    authenticate_user,
    create_access_token,
    get_user,
    optional_current_user,
)

github_sso = GithubSSO(
    settings.GITHUB_CLIENT_ID,
    settings.GITHUB_CLIENT_SECRET,
    f"{settings.HOST}/auth/github/callback",  # TODO: better way to create this?
)

github_sso.is_trused_provider = True

router = APIRouter(prefix="/github")


@router.get("/login", name="auth.providers.github.login", tags=["GitHub SSO"])
async def github_login():
    async with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/connect", name="auth.providers.github.connect", tags=["GitHub SSO"])
async def github_connect():
    """Start GitHub OAuth flow for connecting to existing account"""
    async with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/callback", name="auth.providers.github.callback", tags=["GitHub SSO"])
async def github_callback(
    request: Request, current_user=Depends(optional_current_user)
):
    """Process login response from GitHub and return user info"""
    try:
        async with github_sso:
            github_user = await github_sso.verify_and_process(request)

        async with async_session_maker() as session:
            email = github_user.email
            found_user = await get_user(session, email, github_user.provider)

            if not found_user:
                user_stored = await add_user(
                    session,
                    UserSignUp(
                        email=email,
                    ),
                    github_user.provider,
                    github_user.display_name,
                    is_verified=github_sso.is_trused_provider,
                    existing_user=current_user,
                )

            # Will make sure the user is verified
            # I know this is an extra call, but this way the check is always the same
            user_stored = await authenticate_user(
                session, email=email, provider=github_user.provider
            )

        redirect_url = "/"
        if current_user:
            # If connecting provider to existing account, redirect to profile
            redirect_url = "/profile"

        access_token = await create_access_token(
            user_id=user_stored.id,
            email=user_stored.email,
            provider=github_user.provider,
        )
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        response.set_cookie(settings.COOKIE_NAME, access_token)

        return response

    except DuplicateError as e:
        if current_user:
            # If connecting provider to existing account, redirect to profile with error
            return RedirectResponse(
                url=f"/profile?error={str(e)}", status_code=status.HTTP_302_FOUND
            )
        else:
            # If trying to register with existing email, redirect to login with error
            return RedirectResponse(
                url=f"/login?error={str(e)}", status_code=status.HTTP_302_FOUND
            )

    except oauthlib.oauth2.rfc6749.errors.CustomOAuth2Error:
        raise GenericException(detail="The code passed is incorrect or expired")

    except ValueError:
        logger.exception("Error connecting GitHub provider")
        raise GenericException(detail="An unexpected error occurred")
