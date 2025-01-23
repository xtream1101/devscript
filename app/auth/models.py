import uuid
from datetime import datetime, timezone
from typing import List

from pydantic import validate_email
from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.auth.schemas import UserView
from app.common.constants import SUPPORTED_CODE_THEMES
from app.common.exceptions import ValidationError
from app.common.models import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String(32), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    pending_email: Mapped[str] = mapped_column(String, nullable=True)

    code_theme: Mapped[str | None] = mapped_column(String, nullable=True)

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
    api_keys: Mapped[List["APIKey"]] = relationship(  # noqa: F821 # type: ignore
        "APIKey",
        back_populates="user",
        cascade="all, delete",
    )
    providers: Mapped[List["Provider"]] = relationship(
        "Provider",
        back_populates="user",
        cascade="all, delete",
    )

    @validates("display_name")
    def validate_display_name(self, key, value):
        if value is None or not value.strip():
            raise ValidationError("Display name cannot be empty")

        if len(value.strip()) > User.display_name.type.length:
            raise ValidationError(
                f"Display name cannot be longer than {User.display_name.type.length} characters"
            )
        return value.strip()

    @validates("email", "pending_email")
    def validate_email(self, key, value):
        if not value or not value.strip():
            if key == "email":
                raise ValidationError("Email cannot be empty")
            return None

        try:
            _, value = validate_email(value)
        except ValueError:
            raise ValidationError("Invalid email address")

        return value.lower().strip()

    @validates("code_theme")
    def validate_code_theme(self, key, value):
        if value and value not in SUPPORTED_CODE_THEMES:
            raise ValidationError("Invalid code theme")

        return value

    def to_view(self):
        return UserView(
            id=str(self.id),
            email=self.email,
            display_name=self.display_name,
            registered_at=self.registered_at,
        )


class Provider(Base):
    __tablename__ = "provider"

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="unique_user_provider"),
        UniqueConstraint("email", "name", name="unique_email_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="providers")

    @validates("email")
    def validate_email(self, key, value):
        if value is None or value.strip() == "":
            raise ValidationError("Email cannot be empty")

        try:
            _, value = validate_email(value)
        except ValueError:
            raise ValidationError("Invalid email address")

        return value.lower().strip()


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_used: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["app.models.User"] = relationship(  # noqa: F821 # type: ignore
        "User",
        back_populates="api_keys",
    )

    @validates("name")
    def validate_name(self, key, value):
        if value is not None and value.strip() == "":
            raise ValidationError("Api-key name cannot be empty")

        if len(value.strip()) > APIKey.name.type.length:
            raise ValidationError(
                f"Api-key name cannot be longer than {APIKey.name.type.length} characters"
            )
        return value.strip()
