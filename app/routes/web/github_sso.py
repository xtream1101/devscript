from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.github import GithubSSO
from starlette.requests import Request

from app.auth import create_access_token
from app.models.common import async_session_maker
from app.models.user import DuplicateError, add_user, get_user
from app.schemas import UserSignUp
from app.settings import settings

github_sso = GithubSSO(
    settings.GITHUB_CLIENT_ID,
    settings.GITHUB_CLIENT_SECRET,
    f"{settings.HOST}/v1/github/callback",
)

router = APIRouter(prefix="/v1/github")


@router.get("/login", tags=["GitHub SSO"])
async def github_login():
    async with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/callback", tags=["GitHub SSO"])
async def github_callback(request: Request):
    """Process login response from GitHub and return user info"""

    try:
        async with github_sso:
            user = await github_sso.verify_and_process(request)
        email = user.email
        async with async_session_maker() as session:
            user_stored = await get_user(session, email, user.provider)
            if not user_stored:
                user_to_add = UserSignUp(email=email, fullname=user.display_name)
                user_stored = await add_user(
                    session, user_to_add, provider=user.provider
                )
            access_token = await create_access_token(
                email=user_stored.email, provider=user.provider
            )
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(settings.COOKIE_NAME, access_token)
        return response
    except DuplicateError as e:
        raise HTTPException(status_code=403, detail=f"{e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )
