from typing import List

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

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
        back_populates="tags", secondary=snippet_tags
    )

    def __init__(self, name):
        # Ensure tag meets requirements
        self.id = name.strip()[:16]  # Max length 16, no leading/trailing spaces
        self.id = name.strip()[:16]  # Max length 16, no leading/trailing spaces
        self.id = name.strip()[:16]  # Max length 16, no leading/trailing spaces
