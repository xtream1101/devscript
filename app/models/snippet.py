import uuid
from datetime import datetime, timezone
from typing import List, Optional

import markdown  # Add this import
from pydantic import BaseModel, ValidationInfo, field_validator
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    event,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

import app.models
from app import utils
from app.models.common import Base, async_session_maker


class SnippetView(BaseModel):
    """
    The object that gets passed to the views
    """

    id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    command_name: Optional[str] = None
    public: Optional[bool] = False
    tags: Optional[List[str]] = []
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    forked_from_id: Optional[str] = None

    @field_validator("id", "user_id", "forked_from_id", mode="before")
    def uuid_to_str(cls, v: str, info: ValidationInfo) -> str:
        if v is None:
            return None
        return str(v)

    @property
    def html_description(self):
        return markdown.markdown(self.description) if self.description else None


class Snippet(Base):
    __tablename__ = "snippets"
    __table_args__ = (
        UniqueConstraint("user_id", "command_name", name="unique_user_command_name"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(length=200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(length=50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    command_name: Mapped[Optional[str]] = mapped_column(
        String(length=100), nullable=True
    )
    public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Relationship to tags
    tags: Mapped[List["app.models.Tag"]] = relationship(
        "Tag",
        back_populates="snippets",
        secondary="snippet_tags",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # Relationship to user
    user: Mapped["app.models.User"] = relationship("User", back_populates="snippets")

    # Foreign key to forked snippet
    forked_from_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("snippets.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Self-referential relationship for forks
    forked_from: Mapped["Snippet"] = relationship(
        "Snippet", remote_side=[id], backref="forks"
    )

    def to_view(self):
        return SnippetView(
            id=str(self.id),
            title=self.title,
            content=self.content,
            language=self.language,
            description=self.description,
            command_name=self.command_name,
            public=self.public,
            tags=[tag.id for tag in self.tags],
            user_id=str(self.user_id),
            created_at=self.created_at,
            updated_at=self.updated_at,
            forked_from_id=str(self.forked_from_id) if self.forked_from_id else None,
        )

    @validates("title", "content", "language")
    def non_blank_fields(self, key, value):
        if value is None or value.strip() == "":
            raise ValueError(f"{key.title()} cannot be blank")

        return value.strip()

    @validates("description", "command_name")
    def blank_to_null(self, key, value):
        """
        Convert empty strings to None for nullable fields
        """
        if value is not None and value.strip() == "":
            return None

        return value.strip()


async def _check_command_name_exists(user_id, command_name, exclude_id=None):
    """
    Check if a command name already exists for a user.

    Args:
        user_id: The ID of the user
        command_name: The command name to check
        exclude_id: Optional snippet ID to exclude from the check (used for updates)

    Returns:
        bool: True if command name exists, False otherwise
    """
    if command_name is None or command_name.strip() == "":
        return False

    async with async_session_maker() as session:
        # Use exists() for more efficient query
        query = select(Snippet).where(
            Snippet.user_id == user_id, Snippet.command_name == command_name.strip()
        )

        if exclude_id:
            query = query.where(Snippet.id != exclude_id)

        exists_query = select(query.exists())
        result = await session.execute(exists_query)
        return result.scalar()


@event.listens_for(Snippet, "before_insert")
def snippet_before_insert(mapper, connection, target):
    found_existing = False
    try:
        with utils.sync_await() as await_:
            found_existing = await_(
                _check_command_name_exists(
                    target.user_id, target.command_name, target.id
                )
            )
    except Exception as exc:
        raise exc

    if found_existing:
        raise ValueError("Command name already exists for this user")
