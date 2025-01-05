import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from app import utils
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

    @validates("command_name")
    def validate_command_name(self, key, command_name):
        if not command_name:
            return None

        command_name = command_name.strip()
        if not command_name:
            return None

        found_existing = False
        try:
            with utils.sync_await() as await_:
                found_existing = await_(
                    self.check_command_name_exists(self.user_id, command_name, self.id)
                )
        except Exception as exc:
            raise exc

        if found_existing:
            raise ValueError("Command name already exists for this user")

        return command_name

    async def check_command_name_exists(self, user_id, command_name, exclude_id=None):
        """
        Check if a command name already exists for a user.

        Args:
            user_id: The ID of the user
            command_name: The command name to check
            exclude_id: Optional snippet ID to exclude from the check (used for updates)

        Returns:
            bool: True if command name exists, False otherwise
        """
        if not command_name or command_name.strip() == "":
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
