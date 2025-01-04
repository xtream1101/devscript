import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    select,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models import Base, async_session_maker


class Snippet(Base):
    __tablename__ = "snippets"
    __table_args__ = (
        UniqueConstraint("user_id", "command_name", name="unique_user_command_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(length=200), nullable=False)
    content = Column(Text, nullable=False)
    language = Column(String(length=50), nullable=False)
    description = Column(Text)
    command_name = Column(String(length=100), nullable=True)
    public = Column(Boolean, default=False, nullable=False)
    # Relationship to tags
    tags = relationship("Tag", secondary="snippet_tags", back_populates="snippets")
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(),
        onupdate=datetime.now(),
        nullable=False,
    )

    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # Relationship to user
    user = relationship("User", back_populates="snippets")

    # Foreign key to forked snippet
    forked_from_id = Column(
        UUID(as_uuid=True),
        ForeignKey("snippets.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Self-referential relationship for forks
    forked_from = relationship("Snippet", remote_side=[id], backref="forks")

    def __setattr__(self, name, value):
        if name == "command_name" and value is not None:
            value = value.strip()
            if value == "":
                value = None
        super().__setattr__(name, value)

    @classmethod
    async def check_command_name_exists(cls, user_id, command_name, exclude_id=None):
        """
        Check if a command name already exists for a user.

        Args:
            user_id: The ID of the user
            command_name: The command name to check
            exclude_id: Optional snippet ID to exclude from the check (used for updates)

        Returns:
            bool: True if command name exists, False otherwise
        """
        if not command_name:
            return False

        # Strip whitespace and check if empty
        command_name = command_name.strip()
        if not command_name:
            return False

        async with async_session_maker() as session:
            # Use exists() for more efficient query
            query = select(1).where(
                cls.user_id == user_id, cls.command_name == command_name
            )

            if exclude_id:
                query = query.where(cls.id != exclude_id)

            exists_query = select(query.exists())
            result = await session.execute(exists_query)
            return result.scalar()
