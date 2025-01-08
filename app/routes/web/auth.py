from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from sqlalchemy import select

from app.auth import create_access_token
from app.auth.user import add_user, authenticate_user, optional_current_user
from app.exceptions import DuplicateError
from app.models.common import async_session_maker
from app.models.user import Provider
from app.schemas import User, UserSignUp
from app.settings import settings

router = APIRouter(tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/verify", summary="Verify a user's email")
async def verify_email(request: Request, token: str):
    """
    Verify a user's email.
    """
    async with async_session_maker() as session:
        query = (
            select(Provider)
            .filter(Provider.verify_token == token)
            .filter(Provider.name == "local")
        )
        result = await session.execute(query)
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(status_code=404, detail="Token not found")

        provider.is_verified = True
        provider.verify_token = None

        try:
            await session.commit()
        except Exception as e:
            logger.exception(f"Error verifying email: {e}")
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred. Report this message to support: {e}",
            )

        return RedirectResponse(
            router.url_path_for("login"), status_code=status.HTTP_302_FOUND
        )


@router.post("/register", response_model=User, summary="Register a user")
async def create_user(user_signup: UserSignUp):
    """
    Registers a user.
    """
    async with async_session_maker() as session:
        try:
            user_created = await add_user(session, user_signup, "local")
            return user_created

        except DuplicateError as e:
            raise HTTPException(status_code=403, detail=f"{e}")

        except ValueError as e:
            logger.exception(f"Error creating user: {e}")
            raise HTTPException(status_code=400, detail=f"{e}")

        except Exception as e:
            logger.exception(f"Error creating user: {e}")
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
    async with async_session_maker() as session:
        user = await authenticate_user(session, email=email, password=password)
        if not user:
            raise HTTPException(status_code=403, detail="Invalid email or password.")
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


# Web interface auth routes
@router.get("/login")
async def login_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(request, "auth/login.html")


@router.get("/register")
async def register_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("auth/register.html", {"request": request})
