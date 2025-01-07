from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import (
    authenticate_user,
    create_access_token,
    optional_current_user,
)
from app.models.common import async_session_maker
from app.models.user import DuplicateError, add_user, get_users_stats
from app.schemas import User, UserSignUp
from app.settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/register", response_model=User, summary="Register a user")
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


@router.post("/login", summary="Login as a user")
async def login(
    response: RedirectResponse, email: str = Form(...), password: str = Form(...)
):
    """
    Logs in a user.
    """
    print("login")
    async with async_session_maker() as session:
        user = await authenticate_user(
            session, email=email, password=password, provider="local"
        )
        print(f"user: {user}")
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        try:
            access_token = await create_access_token(email=user.email, provider="local")
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.set_cookie(settings.COOKIE_NAME, access_token)
            return response

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred. Report this message to support: {e}",
            )


@router.post("/logout", summary="Logout a user")
@router.get("/logout", summary="Logout a user")
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
    user: User = Depends(optional_current_user),
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


# Web interface auth routes
@router.get("/login")
async def login_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register")
async def register_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("auth/register.html", {"request": request})
