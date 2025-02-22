from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from loguru import logger
from pydantic import validate_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import SUPPORTED_CODE_THEMES
from app.common.db import get_async_session
from app.common.exceptions import ValidationError
from app.common.templates import templates
from app.common.utils import flash
from app.email.send import send_verification_email
from app.settings import settings

from ...auth.providers.views import providers as list_of_sso_providers
from ..models import APIKey, Provider, User
from ..serializers import TokenDataSerializer
from ..utils import create_token, current_user

router = APIRouter(tags=["Account"])


@router.get(
    "/account", name="auth.account_settings", summary="View user account settings"
)
async def account_settings_view(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Display the user's account settings page with connected providers.
    """
    # Get active API keys for the user
    query = select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active)
    result = await session.execute(query)
    api_keys = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "auth/templates/account_settings.html",
        {
            "pending_email": user.pending_email,
            "code_themes": SUPPORTED_CODE_THEMES,
            "list_of_sso_providers": list_of_sso_providers,
            "api_keys": api_keys,
        },
    )


@router.post(
    "/account/display-name",
    name="auth.update_display_name.post",
    summary="Update display name",
)
async def update_display_name(
    request: Request,
    display_name: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Update the user's display name.
    """
    query = select(User).filter(User.id == user.id)
    result = await session.execute(query)
    db_user = result.scalar_one()

    try:
        db_user.display_name = display_name
    except ValidationError as e:
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error updating display name")
        flash(request, "Failed to update display name", "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/change-email", name="auth.change_email", summary="Change email form")
async def change_email_view(request: Request, user: User = Depends(current_user)):
    """
    Display the change email form.
    """
    return templates.TemplateResponse(request, "auth/templates/change_email.html")


@router.get(
    "/change-email/cancel",
    name="auth.change_email_cancel",
    summary="Cancel email change",
)
async def change_email_cancel(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Cancel the email change process.
    """
    user_query = select(User).filter(User.id == user.id)
    user_result = await session.execute(user_query)
    db_user = user_result.scalar_one()
    db_user.pending_email = None
    await session.commit()

    flash(request, "Email change has been cancelled", "info")
    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/change-email", name="auth.change_email.post", summary="Process email change"
)
async def change_email(
    request: Request,
    new_email: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Initiate email change process. Sends verification email to new address.
    """
    new_email = new_email.strip().lower()
    if new_email == user.email:
        flash(request, "No change, email is the same", "info")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Confirm its a valid email
    try:
        _, new_email = validate_email(new_email)
    except ValueError:
        flash(request, "Invalid email address", "error")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Check if email is used by any other users in the user or providers table
    user_query = select(User).filter(User.email == new_email, User.id != user.id)
    user_result = await session.execute(user_query)
    provider_query = select(Provider).filter(
        Provider.email == new_email, User.id != user.id
    )
    provider_result = await session.execute(provider_query)

    if user_result.first() or provider_result.first():
        flash(request, "Email is already in use", "error")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Check if its already a verified email the user has
    user_providers_query = select(Provider).filter(
        Provider.user_id == user.id, Provider.email == new_email
    )
    user_providers_result = await session.execute(user_providers_query)
    user_providers = user_providers_result.scalars().all()
    if user_providers:
        if all(provider.is_verified for provider in user_providers):
            # All providers with this email are already verified
            # Update the users email and return
            user_query = select(User).filter(User.id == user.id)
            user_result = await session.execute(user_query)
            db_user = user_result.scalar_one()
            db_user.email = new_email
            await session.commit()
            return RedirectResponse(
                url=request.url_for("auth.account_settings"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            flash(request, "Must verify the pending provider request", "error")
            return RedirectResponse(
                url=request.url_for("auth.change_email"),
                status_code=status.HTTP_303_SEE_OTHER,
            )

    # Email is good to use, but needs to be verified
    # Update users pending email
    user_query = select(User).filter(User.id == user.id)
    user_result = await session.execute(user_query)
    db_user = user_result.scalar_one()
    db_user.pending_email = new_email
    await session.commit()

    # Create a token for the new email
    validation_token = await create_token(
        TokenDataSerializer(
            user_id=user.id,
            email=user.email,
            new_email=new_email,
            token_type="validation",
        )
    )
    await send_verification_email(
        new_email, validation_token, from_change_email=user.email
    )
    flash(
        request,
        "A verification email has been sent to the new email address",
        "success",
    )
    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/update-code-theme", name="auth.update_code_theme.post")
async def update_code_theme(
    request: Request,
    theme_mode: str = Form(...),
    code_theme: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update the user's code theme."""
    query = select(User).filter(User.id == user.id)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if theme_mode not in ["light", "dark"]:
        flash(request, "Invalid theme mode", "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if code_theme not in SUPPORTED_CODE_THEMES:
        flash(request, "Invalid code theme", "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if theme_mode == "light":
        db_user.code_theme_light = code_theme
    else:
        db_user.code_theme_dark = code_theme

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error updating code theme")
        flash(request, "Failed to update code theme", "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/reset_code_theme", name="auth.reset_code_theme.post")
async def reset_code_theme(
    request: Request,
    theme_mode: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Reset the user's code theme."""
    query = select(User).filter(User.id == user.id)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if theme_mode not in ["light", "dark"]:
        flash(request, "Invalid theme mode", "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if theme_mode == "light":
        db_user.code_theme_light = None
    else:
        db_user.code_theme_dark = None

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error resetting code theme")
        flash(request, "Failed to reset code theme", "error")
        return RedirectResponse(
            url=request.url_for("auth.account_settings"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/delete", name="auth.delete_account.post", summary="Delete user account")
async def delete_account(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Permanently delete a user's account and all associated data.
    """
    try:
        # Delete the user (which will cascade delete providers, snippets, and api_keys)
        user_query = select(User).filter(User.id == user.id)
        result = await session.execute(user_query)
        user_to_delete = result.scalar_one_or_none()

        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # If user is admin, check if they are the only admin
        if user_to_delete.is_admin:
            admin_count_query = select(User).filter(User.is_admin)
            admin_result = await session.execute(admin_count_query)
            admin_users = admin_result.scalars().all()
            if len(admin_users) <= 1:
                flash(request, "Cannot delete the only admin account", "error")
                return RedirectResponse(
                    url=request.url_for("auth.account_settings"),
                    status_code=status.HTTP_303_SEE_OTHER,
                )

        await session.delete(user_to_delete)
        await session.commit()

        # Clear session cookie and redirect to home
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(settings.COOKIE_NAME)
        return response

    except Exception:
        logger.exception("Error deleting account")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
