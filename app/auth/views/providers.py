from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_session
from app.common.exceptions import ValidationError
from app.common.templates import templates
from app.common.utils import flash

from ..constants import LOCAL_PROVIDER
from ..models import Provider, User
from ..utils import current_user, verify_and_get_password_hash

router = APIRouter(tags=["Providers"])


@router.get(
    "/providers/local/connect",
    name="auth.connect_local",
    summary="Connect local provider",
)
async def connect_local_view(request: Request, user: User = Depends(current_user)):
    """
    Display the connect local provider page.
    """
    return templates.TemplateResponse(
        "auth/templates/connect_local.html",
        {"request": request, "user": user},
    )


@router.post(
    "/providers/local/connect",
    name="auth.connect_local.post",
    summary="Connect local provider",
)
async def connect_local(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    """
    Connect local provider to existing account.
    """
    try:
        if password != confirm_password:
            raise ValidationError("Passwords do not match")

        # Add local provider
        provider = Provider(
            name=LOCAL_PROVIDER,
            email=user.email,
            user_id=user.id,
            is_verified=True,  # Already verified through existing provider
        )
        session.add(provider)

        # Set password for local auth
        # Need to get the user object in this session to update the password
        query = select(User).filter(User.id == user.id)
        result = await session.execute(query)
        db_user = result.scalar_one()
        db_user.password = await verify_and_get_password_hash(password)

        await session.commit()

    except Exception as e:
        if isinstance(e, ValidationError):
            flash(request, str(e), "error")
        else:
            logger.exception(f"Error connecting {LOCAL_PROVIDER} provider")
            flash(request, f"Failed to connect a {LOCAL_PROVIDER} provider", "error")

        await session.rollback()
        return RedirectResponse(
            url=request.url_for("auth.connect_local"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    flash(request, f"{LOCAL_PROVIDER.title()} provider connected", "success")
    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/providers/{provider}/disconnect",
    name="auth.disconnect_provider.post",
    summary="Disconnect an authentication provider",
)
async def disconnect_provider(
    provider: str,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Disconnect an authentication provider from the user's account.
    Ensures at least one provider remains connected.
    """
    if len(user.providers) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect your only authentication provider.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    if provider_to_remove.name == LOCAL_PROVIDER:
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while disconnecting provider.",
        )

    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
