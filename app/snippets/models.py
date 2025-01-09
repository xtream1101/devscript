import uuid
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
    func,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.common import utils
from app.common.db import async_session_maker
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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(length=50), nullable=False)
    command_name: Mapped[Optional[str]] = mapped_column(
        String(length=100), nullable=True
    )
    public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Relationship to tags
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        back_populates="snippets",
        secondary="snippet_tags",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(timezone="utc"), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(timezone="utc"),
        server_onupdate=func.now(timezone="utc"),
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
    # Self-referential relationship for forks
    forked_from: Mapped["Snippet"] = relationship(
        "Snippet", remote_side=[id], backref="forks"
    )

    def to_view(self):
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
            created_at=self.created_at,
            updated_at=self.updated_at,
            forked_from_id=str(self.forked_from_id) if self.forked_from_id else None,
        )

    def to_card_view(self):
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
        if value is None or value.strip() == "":
            return None

        return value.strip()


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

        id = id.strip()
        if len(id) > 16:
            raise ValueError(f"Tag is too long: '{id}'")

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
        tag_names = [t.strip() for t in tag_names if t.strip()]
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
        raise ValueError("Command name already exists for this user")
