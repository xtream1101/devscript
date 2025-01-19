from datetime import datetime
from typing import List, Optional

import markdown
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from app.auth.models import User
from app.auth.schemas import UserView


class SnippetView(BaseModel):
    """
    The object that gets passed to the views
    """

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    command_name: Optional[str] = None
    public: Optional[bool] = False
    tags: Optional[List[str]] = []
    user_id: Optional[str] = None
    user: Optional[UserView] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    forked_from_id: Optional[str] = None
    is_fork: Optional[bool] = False
    is_favorite: Optional[bool] = False

    @field_validator("id", "user_id", "forked_from_id", mode="before")
    def uuid_to_str(cls, v: str, info: ValidationInfo) -> str:
        if v is None:
            return None
        return str(v)

    @field_validator("user", mode="before")
    def user_to_view(cls, user: User, info: ValidationInfo) -> UserView | None:
        return user.to_view() if user else None

    @property
    def html_description(self):
        return (
            markdown.markdown(
                self.description,
                extensions=[
                    "pymdownx.extra",
                    "pymdownx.tasklist",
                    "sane_lists",
                ],
            )
            if self.description
            else None
        )


class SnippetCardView(BaseModel):
    """
    The object that gets passed to the snippet card views
    """

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    command_name: Optional[str] = None
    public: Optional[bool] = False
    tags: Optional[List[str]] = []
    user_id: Optional[str] = None
    user: Optional[UserView] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    forked_from_id: Optional[str] = None
    is_fork: Optional[bool] = False
    is_favorite: Optional[bool] = False

    @field_validator("id", "user_id", "forked_from_id", mode="before")
    def uuid_to_str(cls, v: str, info: ValidationInfo) -> str:
        if v is None:
            return None
        return str(v)

    @field_validator("user", mode="before")
    def user_to_view(cls, user: User, info: ValidationInfo) -> UserView | None:
        return user.to_view() if user else None

    @property
    def content_truncated(self):
        if self.content is None:
            return ""

        return self.content[:200] + "..." if len(self.content) > 200 else self.content
