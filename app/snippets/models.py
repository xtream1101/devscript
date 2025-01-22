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
from app.common.db import async_session_maker
from app.common.exceptions import ValidationError
from app.common.models import Base

from .schemas import SnippetCardView, SnippetView


class Snippet(Base):
    __tablename__ = "snippets"
    __table_args__ = (
        UniqueConstraint("user_id", "command_name", name="unique_user_command_name"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(length=200), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(length=200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(length=50), nullable=False)
    command_name: Mapped[Optional[str]] = mapped_column(
        String(length=32), nullable=True
    )
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
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # Relationship to user
    user: Mapped["app.auth.models.User"] = relationship(  # noqa: F821 # type: ignore
        "User",
        back_populates="snippets",
    )

    # Foreign key to forked snippet
    forked_from_id: Mapped[UUID] = mapped_column(
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

    def to_view(self, user=None):
        is_favorite = self.is_favorite(user.id) if user else False

        return SnippetView(
            id=str(self.id),
            title=self.title,
            subtitle=self.subtitle,
            content=self.content,
            language=self.language,
            description=self.description,
            command_name=self.command_name,
            public=self.public,
            tags=[tag.id for tag in self.tags],
            user_id=str(self.user_id),
            user=self.user,
            created_at=self.created_at,
            updated_at=self.updated_at,
            is_fork=self.is_fork,
            forked_from_id=str(self.forked_from_id) if self.forked_from_id else None,
            is_favorite=is_favorite,
        )

    def to_card_view(self, user=None):
        is_favorite = self.is_favorite(user.id) if user else False

        return SnippetCardView(
            id=str(self.id),
            title=self.title,
            subtitle=self.subtitle,
            content=self.content,
            language=self.language,
            command_name=self.command_name,
            public=self.public,
            tags=[tag.id for tag in self.tags],
            user_id=str(self.user_id),
            user=self.user,
            created_at=self.created_at,
            updated_at=self.updated_at,
            is_fork=self.is_fork,
            forked_from_id=str(self.forked_from_id) if self.forked_from_id else None,
            is_favorite=is_favorite,
        )

    @validates("title", "language")
    def non_blank_fields(self, key, value):
        if value is None or value.strip() == "":
            raise ValueError(f"{key.title()} cannot be blank")

        return value.strip()

    @validates("description", "content")
    def blank_to_null(self, key, value):
        """
        Convert empty strings to None for nullable fields
        """
        if value is None or value.strip() == "":
            return None

        return value.strip()

    @validates("command_name")
    def validate_command_name(self, key, command_name):
        if command_name is None or command_name.strip() == "":
            return None

        if len(command_name) > Snippet.command_name.type.length:
            raise ValidationError(
                f"Command name cannot be longer than {Snippet.command_name.type.length} characters"
            )

        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
        if not all(c in allowed_chars for c in command_name):
            raise ValidationError(
                "Command name can only contain lowercase letters, numbers, hyphens, and underscores"
            )

        return command_name.strip()

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
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(
        String(length=16), primary_key=True
    )  # Using the tag name as the ID
    snippets: Mapped[List["Snippet"]] = relationship(
        "Snippet",
        back_populates="tags",
        secondary=snippet_tags,
    )

    @validates("id")
    def validate_id(self, key, id):
        if id is None or id.strip() == "":
            raise ValueError("Tag cannot be empty")

        id = id.strip().lower()
        if len(id) > 16:
            raise ValueError(f"Tag is too long: '{id}'")

        # Limit only to subset of chars
        if not all(
            c.isalnum() or c in ["_", "-", " ", ".", ":", "/", "\\"] for c in id
        ):
            raise ValueError(f"Tag contains invalid characters: '{id}'")

        # TODO: Set some type of char limit on the tag name?

        return id

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
        existing_tags = await session.execute(select(Tag).where(Tag.id.in_(tag_names)))
        existing_tags = existing_tags.scalars().all()
        existing_tag_ids = {tag.id for tag in existing_tags}

        # Create new tags for any that don't exist
        new_tags = []
        for tag_name in tag_names:
            if tag_name not in existing_tag_ids:
                tag = Tag(id=tag_name)
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
