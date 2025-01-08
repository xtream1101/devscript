from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.github import GithubSSO
from loguru import logger
from starlette.requests import Request

from app.auth import create_access_token
from app.auth.user import add_user, get_user
from app.exceptions import DuplicateError
from app.models.common import async_session_maker
from app.schemas import UserSignUp
from app.settings import settings

github_sso = GithubSSO(
    settings.GITHUB_CLIENT_ID,
    settings.GITHUB_CLIENT_SECRET,
    f"{settings.HOST}/api/auth/github/callback",  # TODO: better way to create this?
)

router = APIRouter(prefix="/github")


@router.get("/login", tags=["GitHub SSO"])
async def github_login():
    async with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/callback", tags=["GitHub SSO"])
async def github_callback(request: Request):
    """Process login response from GitHub and return user info"""

    try:
        async with github_sso:
            github_user = await github_sso.verify_and_process(request)
        email = github_user.email
        async with async_session_maker() as session:
            user_stored = await get_user(session, email, github_user.provider)
            if not user_stored:
                # Github is a trusted sso provider, so auto verify
                user_to_add = UserSignUp(
                    email=email, display_name=github_user.display_name, is_verified=True
                )
                user_stored = await add_user(
                    session, user_to_add, provider_name=github_user.provider
                )
            access_token = await create_access_token(
                email=user_stored.email, provider=github_user.provider
            )
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(settings.COOKIE_NAME, access_token)
        return response
    except DuplicateError as e:
        raise HTTPException(status_code=403, detail=f"{e}")
    except ValueError as e:
        logger.exception(e)
        raise HTTPException(status_code=400, detail=f"{e}")
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )
