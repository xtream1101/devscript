from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.db import async_session_maker
from app.common.exceptions import DuplicateError
from app.common.templates import templates
from app.settings import settings

from .models import Provider
from .models import User as UserModel
from .schemas import User, UserSignUp
from .utils import (
    add_user,
    authenticate_user,
    create_access_token,
    current_user,
    optional_current_user,
)

router = APIRouter(tags=["Auth"])


@router.get("/profile", name="auth.profile", summary="View user profile")
async def profile_view(request: Request, user: User = Depends(current_user)):
    """
    Display the user's profile page with connected providers.
    """
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "auth/templates/profile.html",
        {"request": request, "user": user, "error": error},
    )


@router.post(
    "/providers/{provider}/disconnect",
    name="auth.disconnect_provider",
    summary="Disconnect an authentication provider",
)
async def disconnect_provider(
    provider: str,
    request: Request,
    user: User = Depends(current_user),
):
    """
    Disconnect an authentication provider from the user's account.
    Ensures at least one provider remains connected.
    """
    if len(user.providers) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot disconnect your only authentication provider.",
        )

    async with async_session_maker() as session:
        # Find and delete the provider
        query = (
            select(Provider)
            .filter(Provider.user_id == user.id)
            .filter(Provider.name == provider)
            .options(selectinload(Provider.user))
        )
        result = await session.execute(query)
        provider_to_remove = result.scalar_one_or_none()

        if not provider_to_remove:
            raise HTTPException(status_code=404, detail="Provider not found")

        if provider_to_remove.name == "local":
            # Clear the password since its only for the local provider
            # Need to use the user object through the provider row as the passed
            # in user object is in a different session
            provider_to_remove.user.password = None

        await session.delete(provider_to_remove)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Error disconnecting provider")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while disconnecting provider.",
            )

        return RedirectResponse(
            url=request.url_for("auth.profile"), status_code=status.HTTP_302_FOUND
        )


@router.get("/verify", name="auth.verify_email", summary="Verify a user's email")
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
        except Exception:
            logger.exception("Error verifying email")
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred.",
            )

        return RedirectResponse(
            request.url_for("auth.login"), status_code=status.HTTP_302_FOUND
        )


@router.get("/register", name="auth.register", summary="Register a user")
async def register_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "auth/templates/register.html", {"request": request}
    )


@router.post(
    "/register",
    name="auth.register.post",
    response_model=User,
    summary="Register a user",
)
async def register(user_signup: UserSignUp):
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
            raise HTTPException(status_code=400, detail=f"{e}")

        except Exception:
            logger.exception("Error creating user")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred.",
            )


@router.get("/login", name="auth.login", summary="Login as a user")
async def login_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(request, "auth/templates/login.html")


@router.post("/login", name="auth.login.post", summary="Login as a user")
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

        except Exception:
            logger.exception("Error logging user in")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred.",
            )


@router.get("/logout", name="auth.logout", summary="Logout a user")
@router.post("/logout", name="auth.logout.post", summary="Logout a user")
async def logout():
    """
    Logout a user.
    """
    try:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.delete_cookie(settings.COOKIE_NAME)
        return response
    except Exception:
        logger.exception("Error logging user out")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )


@router.post("/delete", name="auth.delete_account", summary="Delete user account")
async def delete_account(request: Request, user: User = Depends(current_user)):
    """
    Permanently delete a user's account and all associated data.
    """
    try:
        async with async_session_maker() as session:
            # Delete the user (which will cascade delete providers, snippets, and api_keys)
            user_query = select(UserModel).filter(UserModel.id == user.id)
            result = await session.execute(user_query)
            user_to_delete = result.scalar_one_or_none()

            if not user_to_delete:
                raise HTTPException(status_code=404, detail="User not found")

            await session.delete(user_to_delete)
            await session.commit()

            # Clear session cookie and redirect to home
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.delete_cookie(settings.COOKIE_NAME)
            return response

    except Exception:
        logger.exception("Error deleting account")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )
