import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.common.constants import SUPPORTED_LANGUAGES
from app.common.exceptions import ValidationError
from app.common.models import Base

from .serializers import SnippetSerializer


# =================================================================================
#
# Snippet Model
#
# =================================================================================
class Snippet(Base):
    __tablename__ = "snippets"
    __table_args__ = (
        UniqueConstraint("user_id", "command_name", name="unique_user_command_name"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
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
        order_by="asc(SnippetTag.order),asc(SnippetTag.created_at),Tag.name",
        viewonly=True,
    )
    tag_associations: Mapped[List["SnippetTag"]] = relationship(
        "SnippetTag",
        back_populates="snippet",
        cascade="all, delete-orphan",
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

    def to_serializer(self, user=None):
        is_favorite = self.is_favorite(user.id) if user else False
        return SnippetSerializer(
            **self.as_dict,
            is_favorite=is_favorite,
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

    async def bulk_add_tags(
        self,
        session: AsyncSession,
        tag_names: List[str],
    ) -> List["SnippetTag"]:
        """
        Create any tags that dont exist and return a list of all tags.

        Args:
            session: AsyncSession to use for the database queries.
            tag_names: List of tag names to set for the snippet.
            snippet_id: ID of the snippet to add tags to (optional).
        """
        # Remove duplicates and empty tags
        #   Sets don't preserve order, so we're using a dict to keep the order
        tag_names = list(
            dict.fromkeys([t.strip().lower() for t in tag_names if t.strip()])
        )

        # If no tags, return empty list
        if not tag_names:
            return []

        # Get all existing tags in one query
        existing_tags = await session.execute(
            select(Tag).where(Tag.name.in_(tag_names))
        )
        existing_tags = existing_tags.scalars().all()

        # Get all existing tags for the snippet
        existing_snippet_tags = await session.execute(
            select(SnippetTag).where(SnippetTag.snippet_id == self.id)
        )
        existing_snippet_tags = existing_snippet_tags.scalars().all()

        ordered_snippet_tags = []
        for i, tag_name in enumerate(tag_names):
            # Check if the tag already exists for the snippet
            # If it does, update the order
            snippet_tag = next(
                (st for st in existing_snippet_tags if st.tag_name == tag_name), None
            )
            if snippet_tag:
                snippet_tag.order = i
                session.add(snippet_tag)
                ordered_snippet_tags.append(snippet_tag)
                continue

            # Check if the tag already exists in the database
            # If it doesn't, create a new tag
            tag = next((tag for tag in existing_tags if tag.name == tag_name), None)
            if not tag:
                tag = Tag(name=tag_name)
                session.add(tag)

            # Create a new snippet tag
            snippet_tag = SnippetTag(snippet=self, tag=tag, order=i)
            session.add(snippet_tag)
            ordered_snippet_tags.append(snippet_tag)

        return ordered_snippet_tags


# =================================================================================
#
# Tag Model
#
# =================================================================================
class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    snippets: Mapped[List["Snippet"]] = relationship(
        "Snippet",
        back_populates="tags",
        secondary="snippet_tags",
        viewonly=True,
    )
    snippet_associations: Mapped[List["SnippetTag"]] = relationship(
        "SnippetTag",
        back_populates="tag",
        cascade="all, delete-orphan",
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


# =================================================================================
#
# Snippet Tags Association Table
#
# =================================================================================
class SnippetTag(Base):
    __tablename__ = "snippet_tags"

    snippet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("snippets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_name: Mapped[str] = mapped_column(
        String(32), ForeignKey("tags.name", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    snippet = relationship("Snippet", back_populates="tag_associations")
    tag = relationship("Tag", back_populates="snippet_associations")


# =================================================================================
#
# Favorites Association Table
#
# =================================================================================
favorites = Table(
    "favorites",
    Base.metadata,
    Column(
        "snippet_id", ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
)
