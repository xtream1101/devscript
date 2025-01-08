import secrets
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.utils import current_active_user
from app.common.db import get_async_session
from app.common.templates import templates

from .models import APIKey

router = APIRouter()


@router.get("/", name="api_keys.index")
async def index(
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Show the API keys management page."""
    query = select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active.is_(True))
    result = await session.execute(query)
    api_keys = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "api_keys/templates/index.html",
        {"api_keys": api_keys},
    )


@router.post("/", name="api_key.create.post")
async def create_api_key(
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
):
    """Create a new API key."""
    # Generate a random API key
    api_key = secrets.token_urlsafe(32)

    # Create new API key record
    db_api_key = APIKey(key=api_key, name=name, user_id=user.id)
    session.add(db_api_key)
    await session.commit()

    # Get all active API keys
    query = select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active.is_(True))
    result = await session.execute(query)
    api_keys = result.scalars().all()

    # Show the key only once
    return templates.TemplateResponse(
        request,
        "api_keys/templates/index.html",
        {
            "api_keys": api_keys,
            "api_key": api_key,
        },
    )


@router.post("/{key_id}/revoke", name="api_key.revoke.post")
async def revoke_api_key(
    request: Request,
    key_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Revoke an API key."""
    # First verify the key belongs to the user
    query = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    result = await session.execute(query)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Update the key to be inactive
    await session.execute(
        update(APIKey).where(APIKey.id == key_id).values(is_active=False)
    )
    await session.commit()

    return RedirectResponse(url=request.url_for("api_keys.index"), status_code=303)
