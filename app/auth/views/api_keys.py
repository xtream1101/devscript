import secrets
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_session
from app.common.exceptions import ValidationError
from app.common.utils import flash

from ..models import APIKey, User
from ..utils import current_user

router = APIRouter(tags=["API Keys"])


@router.post("/api-keys", name="api_key.create.post")
async def create_api_key(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
):
    """Create a new API key."""
    try:
        # Generate a random API key
        api_key = secrets.token_urlsafe(32)

        # Create new API key record
        db_api_key = APIKey(key=api_key, name=name, user_id=user.id)
        session.add(db_api_key)
        await session.commit()

    except Exception as e:
        if isinstance(e, ValidationError):
            flash(request, str(e), level="error")
        else:
            flash(request, "An error occurred", level="error")
            logger.exception("Error creating api-key")
    else:
        flash(
            request,
            "API key created successfully",
            level="success",
            format="new_api_key",
            api_key=api_key,
        )

    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/api-keys/{key_id}/revoke", name="api_key.revoke.post")
async def revoke_api_key(
    request: Request,
    key_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Revoke an API key."""
    # First verify the key belongs to the user
    query = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    result = await session.execute(query)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Update the key to be inactive
    api_key.is_active = False
    await session.commit()

    return RedirectResponse(
        url=request.url_for("auth.account_settings"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
