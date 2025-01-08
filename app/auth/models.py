import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base


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
        DateTime, default=datetime.now(timezone.utc)
    )

    snippets: Mapped[List["app.snippets.models.Snippet"]] = relationship(
        "Snippet", back_populates="user", cascade="all, delete"
    )
    api_keys: Mapped[List["app.api_keys.models.APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete",
    )
    providers: Mapped[List["Provider"]] = relationship(
        "Provider", back_populates="user"
    )

    @property
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Provider(Base):
    __tablename__ = "provider"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[String] = mapped_column(String, nullable=False)
    email: Mapped[String] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    # Only really needed for local/untrusted providers
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verify_token: Mapped[String] = mapped_column(String, nullable=True, default=None)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="providers")

    # Add a unique constraint to ensure only one provider per user
    __table_args__ = (UniqueConstraint("name", "user_id"),)

    @property
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
