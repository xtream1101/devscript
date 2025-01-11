import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.common.models import Base


class User(Base):
    __tablename__ = "user"

    # TODO: Update to use 2.0 column spec
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[String] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[String] = mapped_column(String, nullable=True)
    display_name: Mapped[String] = mapped_column(String, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(timezone="utc")
    )

    snippets: Mapped[List["app.snippets.models.Snippet"]] = relationship(  # noqa: F821 # type: ignore
        "Snippet",
        back_populates="user",
        cascade="all, delete",
    )
    favorites: Mapped[List["app.snippets.models.Snippet"]] = relationship(  # noqa: F821 # type: ignore
        "Snippet",
        secondary="favorites",
        back_populates="favorited_by",
        cascade="all, delete",
    )
    api_keys: Mapped[List["app.api_keys.models.APIKey"]] = relationship(  # noqa: F821 # type: ignore
        "APIKey",
        back_populates="user",
        cascade="all, delete",
    )
    providers: Mapped[List["Provider"]] = relationship(
        "Provider",
        back_populates="user",
        cascade="all, delete",
    )

    @validates("email")
    def validate_email(self, key, email):
        return email.lower().strip()

    @property
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Provider(Base):
    __tablename__ = "provider"

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_user_provider"),
        UniqueConstraint("email", "name", name="unique_email_provider"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[String] = mapped_column(String, nullable=False)
    email: Mapped[String] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(timezone="utc")
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="providers")

    @validates("email")
    def validate_email(self, key, email):
        return email.lower().strip()

    @property
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ValidationToken(Base):
    __tablename__ = "validation_token"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token: Mapped[String] = mapped_column(
        String,
        nullable=False,
        # TODO: Use something better then a uuid for this task
        default=lambda: str(uuid.uuid4()),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # This ensures SQLAlchemy maintains timezone info
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # If no provider id is set, that means we are validating the users primary email
    provider_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[String] = mapped_column(String, nullable=False)

    user: Mapped["User"] = relationship("User")
    provider: Mapped["Provider"] = relationship("Provider")

    @property
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
