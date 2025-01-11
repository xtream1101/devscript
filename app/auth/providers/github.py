from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.github import GithubSSO
from loguru import logger
from starlette.requests import Request

from app.common.db import async_session_maker
from app.common.exceptions import DuplicateError
from app.settings import settings

from ..schemas import UserSignUp
from ..utils import (
    add_user,
    check_email_exists,
    create_access_token,
    get_user,
    optional_current_user,
)

github_sso = GithubSSO(
    settings.GITHUB_CLIENT_ID,
    settings.GITHUB_CLIENT_SECRET,
    f"{settings.HOST}/auth/github/callback",  # TODO: better way to create this?
)

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

        email = github_user.email
        async with async_session_maker() as session:
            """
            Signup conditions:
                - if current_user
                - if email does not exists at all in the db

            Login conditions:
                - email & provider exists in the provider table

            Error conditions:
                - if email exists in the user or provider table but not an email & provider together

            """
            if_email_exists = await check_email_exists(session, email)
            found_user = await get_user(session, email, github_user.provider)

            if found_user:
                # User & provider exists, so login
                user_stored = found_user
                redirect_url = "/"

            elif current_user or not if_email_exists:
                # Add provider flow, either to a new account or an existing one
                user_stored = await add_user(
                    session,
                    UserSignUp(
                        email=email,
                        display_name=github_user.display_name,
                    ),
                    github_user.provider,
                    is_verified=True,
                    existing_user=current_user,
                )
                if current_user:
                    # If connecting provider to existing account, redirect to profile
                    redirect_url = "/profile"
                else:
                    redirect_url = "/"

            elif if_email_exists:
                # If email exists in the user or provider table but not an email & provider together
                raise DuplicateError(
                    "Please add this provider by loging into your existing account first"
                )

        access_token = await create_access_token(
            email=user_stored.email, provider=github_user.provider
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

    except ValueError as e:
        logger.exception("Error connecting GitHub provider")
        raise HTTPException(status_code=400, detail=f"{e}")

    except Exception:
        logger.exception("Error connecting GitHub provider")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )
