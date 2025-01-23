from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.common.db import get_async_session

from .models import APIKey

router = APIRouter()


async def get_api_key_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Get a user from an API key. Used for API key authentication."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is required"
        )

    query = select(APIKey).where(APIKey.key == x_api_key, APIKey.is_active)
    result = await session.execute(query)
    db_api_key = result.scalar_one_or_none()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    # Update last_used timestamp
    db_api_key.last_used = datetime.now(timezone.utc)
    await session.commit()

    # Get the user
    query = select(User).where(User.id == db_api_key.user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user
