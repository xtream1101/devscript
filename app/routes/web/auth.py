from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.models.common import async_session_maker
from app.models.user import DuplicateError, add_user, get_users_stats
from app.schemas import User, UserSignUp
from app.settings import settings

router = APIRouter(prefix="/v1")
templates = Jinja2Templates(directory="app/templates")


@router.post("/sign_up", response_model=User, summary="Register a user", tags=["Auth"])
async def create_user(user_signup: UserSignUp):
    """
    Registers a user.
    """
    async with async_session_maker() as session:
        try:
            user_created = await add_user(session, user_signup)
            return user_created

        except DuplicateError as e:
            raise HTTPException(status_code=403, detail=f"{e}")

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{e}")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred. Report this message to support: {e}",
            )


@router.post("/login", summary="Login as a user", tags=["Auth"])
async def login(
    response: RedirectResponse, username: str = Form(...), password: str = Form(...)
):
    """
    Logs in a user.
    """
    async with async_session_maker() as session:
        user = await authenticate_user(
            session, username=username, password=password, provider="local"
        )
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        try:
            access_token = await create_access_token(
                username=user.username, provider="local"
            )
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.set_cookie(settings.COOKIE_NAME, access_token)
            return response

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred. Report this message to support: {e}",
            )


@router.post("/logout", summary="Logout a user", tags=["Auth"])
async def logout():
    """
    Logout a user.
    """
    try:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.delete_cookie(settings.COOKIE_NAME)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )


@router.get("/new-auth", response_class=HTMLResponse, summary="Home page")
async def home_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """
    Returns all users.
    """
    versions = {
        "fastapi_version": "3",
        "fastapi_sso_version": "3",
    }
    try:
        if user is not None:
            async with async_session_maker() as session:
                users_stats = await get_users_stats(session)
            response = templates.TemplateResponse(
                "auth2/index.html",
                {
                    "request": request,
                    "user": user,
                    "users_stats": users_stats,
                    **versions,
                },
            )
        else:
            response = templates.TemplateResponse(
                "auth2/login.html", {"request": request, **versions}
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred. Report this message to support: {e}",
        )
