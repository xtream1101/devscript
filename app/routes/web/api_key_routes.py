import secrets
import uuid

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.db import get_async_session
from app.users import current_active_user
from app.models.user import User

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/")
async def api_keys_page(
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Show the API keys management page."""
    query = select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active.is_(True))
    result = await session.execute(query)
    api_keys = result.scalars().all()

    return templates.TemplateResponse(
        "api_keys.html", {"request": request, "user": user, "api_keys": api_keys}
    )


@router.post("/")
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
        "api_keys.html",
        {
            "request": request,
            "user": user,
            "api_keys": api_keys,
            "api_key": api_key,
        },
    )


@router.post("/{key_id}/revoke")
async def revoke_api_key(
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

    return RedirectResponse(url="/api-keys", status_code=303)
