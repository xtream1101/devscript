import uuid
from datetime import datetime, timezone
from typing import List

from passlib.context import CryptContext
from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    String,
    UniqueConstraint,
    desc,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship

import app.models
import app.schemas as schemas
from app.models.common import Base


class User(Base):
    __tablename__ = "user"

    # TODO: Update to use 2.0 column spec
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email = Column(String)
    password = Column(String, nullable=True)
    provider = Column(String, default="local", nullable=True)
    fullname = Column(String, nullable=True)
    register_date = Column(
        DateTime,
        default=datetime.now(timezone.utc),
    )

    snippets: Mapped[List["app.models.Snippet"]] = relationship(
        "Snippet", back_populates="user", cascade="all, delete"
    )
    api_keys: Mapped[List["app.models.APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete",
    )

    __table_args__ = (
        UniqueConstraint("email", "provider", name="unique_email_per_provider"),
    )

    @property
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class DuplicateError(Exception):
    pass


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password):
    return pwd_context.hash(password)


async def add_user(session, user: schemas.UserSignUp, provider: str = None):
    if not provider and not user.password:
        raise ValueError("A password should be provided for non SSO registers")
    elif provider and user.password:
        raise ValueError("A password should not be provided for SSO registers")

    if user.password:
        password = await get_password_hash(user.password)
    else:
        password = None

    user = User(
        email=user.email,
        password=password,
        fullname=user.fullname,
        provider=provider,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise DuplicateError(
            f"email {user.email} is already attached to a "
            "registered user for the provider '{provider}'."
        )
    return user


async def get_user(session, email: str, provider: str):
    query = select(User).filter(User.email == email).filter(User.provider == provider)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_users_stats(session):
    query = (
        select(User)
        .with_only_columns(
            User.provider.label("provider"),
            func.count(User.provider).label("count"),
        )
        .group_by(User.provider)
        .order_by(desc("count"))
    )
    result = await session.execute(query)
    records = result.all()

    users_stats = [
        schemas.UserStat(provider=record[0], count=record[1]) for record in records
    ]
    return users_stats
