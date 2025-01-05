from typing import List

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

import app.models
from app.models.common import Base

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
    snippets: Mapped[List["app.models.Snippet"]] = relationship(
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
