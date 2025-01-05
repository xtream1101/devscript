from typing import List

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, relationship

from app.models import Base, get_async_session


class User(SQLAlchemyBaseUserTableUUID, Base):
    snippets: Mapped[List["Snippet"]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user", cascade="all, delete"
    )


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
