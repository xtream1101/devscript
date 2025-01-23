import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.common import utils
from app.common.constants import SUPPORTED_LANGUAGES
from app.common.db import async_session_maker
from app.common.exceptions import ValidationError
from app.common.models import Base

from .serializers import SnippetSerializer


class Snippet(Base):
    __tablename__ = "snippets"
    __table_args__ = (
        UniqueConstraint("user_id", "command_name", name="unique_user_command_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    command_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Relationship to tags
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        back_populates="snippets",
        secondary="snippet_tags",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # Relationship to user
    user: Mapped["app.auth.models.User"] = relationship(  # noqa: F821 # type: ignore
        "User",
        back_populates="snippets",
    )

    # Foreign key to forked snippet
    forked_from_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("snippets.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Self-referential relationship for forks
    forked_from: Mapped["Snippet"] = relationship(
        "Snippet", remote_side=[id], backref="forks"
    )

    # Relationship to favorites
    favorited_by: Mapped[List["app.auth.models.User"]] = relationship(  # noqa: F821 # type: ignore
        "User",
        secondary="favorites",
        back_populates="favorites",
    )

    @validates("title", "language")
    def non_blank_fields(self, key, value):
        if value is None or value.strip() == "":
            raise ValidationError(f"{key.title()} cannot be blank")

        if key == "language" and value not in SUPPORTED_LANGUAGES.__members__:
            raise ValidationError(f"Unsupported language: {value}")

        if key == "title" and len(value.strip()) > Snippet.title.type.length:
            raise ValidationError(
                f"Title cannot be longer than {Snippet.title.type.length} characters"
            )

        return value.strip()

    @validates("description", "content", "subtitle")
    def blank_to_null(self, key, value):
        """
        Convert empty strings to None for nullable fields
        """
        if value is None or value.strip() == "":
            return None

        if key == "subtitle" and len(value.strip()) > Snippet.subtitle.type.length:
            raise ValidationError(
                f"Subtitle cannot be longer than {Snippet.subtitle.type.length} characters"
            )

        content_size = 50_000
        if key == "content" and len(value) > content_size:
            raise ValidationError(
                f"Snippet cannot be larger than {'{:,}'.format(content_size)} characters"
            )

        if key == "description" and len(value) > content_size:
            raise ValidationError(
                f"Description cannot be larger than {'{:,}'.format(content_size)} characters"
            )

        return value.strip()

    @validates("command_name")
    def validate_command_name(self, key, value):
        if value is None or value.strip() == "":
            return None

        if len(value.strip()) > Snippet.command_name.type.length:
            raise ValidationError(
                f"Command name cannot be longer than {Snippet.command_name.type.length} characters"
            )

        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
        if not all(c in allowed_chars for c in value):
            raise ValidationError(
                "Command name can only contain alphanumeric, hyphens, and underscores"
            )

        return value.strip()

    def to_view(self, user=None):
        is_favorite = self.is_favorite(user.id) if user else False
        tags = [tag.name for tag in self.tags]

        return SnippetSerializer(
            **self.as_dict,
            is_favorite=is_favorite,
            tags=tags,
        )

    def is_favorite(self, user_id):
        """
        Check if the snippet is favorited by a user.

        Args:
            user_id: The ID of the user

        Returns:
            bool: True if the snippet is favorited by the user, False otherwise
        """
        return any(user.id == user_id for user in self.favorited_by)


# Association table for many-to-many relationship
favorites = Table(
    "favorites",
    Base.metadata,
    Column(
        "snippet_id", ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
)


# Association table for many-to-many relationship
snippet_tags = Table(
    "snippet_tags",
    Base.metadata,
    Column(
        "snippet_id", ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("tag_name", ForeignKey("tags.name", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    snippets: Mapped[List["Snippet"]] = relationship(
        "Snippet",
        back_populates="tags",
        secondary=snippet_tags,
    )

    @validates("name")
    def validate_name(self, key, value):
        if value is None or value.strip() == "":
            raise ValidationError("Tag cannot be empty")

        value = value.strip().lower()
        if len(value) > Tag.name.type.length:
            raise ValidationError(f"Tag is too long: '{value}'")

        # Limit only to subset of chars
        if not all(
            c.isalnum() or c in ["_", "-", " ", ".", ":", "/", "\\"] for c in value
        ):
            raise ValidationError(f"Tag contains invalid characters: '{value}'")

        return value

    @classmethod
    async def bulk_add_tags(
        cls, session: AsyncSession, tag_names: List[str]
    ) -> List["Tag"]:
        """
        Create any tags that dont exist and return a list of all tags.

        Args:
            session: AsyncSession to use for the database queries.
            tag_names: List of tag names to set for the snippet.
        """
        tag_names = set([t.strip().lower() for t in tag_names if t.strip()])
        # Get all existing tags in one query
        existing_tags = await session.execute(
            select(Tag).where(Tag.name.in_(tag_names))
        )
        existing_tags = existing_tags.scalars().all()
        existing_tag_names = {tag.name for tag in existing_tags}

        # Create new tags for any that don't exist
        new_tags = []
        for tag_name in tag_names:
            if tag_name not in existing_tag_names:
                tag = Tag(name=tag_name)
                new_tags.append(tag)
                session.add(tag)

        await session.commit()

        return list(existing_tags) + new_tags


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
        query = select(Snippet).where(
            Snippet.user_id == user_id, Snippet.command_name == command_name.strip()
        )

        if exclude_id:
            query = query.where(Snippet.id != exclude_id)

        exists_query = select(query.exists())
        result = await session.execute(exists_query)
        return result.scalar()


@event.listens_for(Snippet, "before_insert")
@event.listens_for(Snippet, "before_update")
def snippet_before_upsert(mapper, connection, target):
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
        raise ValidationError("Command name already exists for this user")
