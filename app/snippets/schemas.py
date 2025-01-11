from datetime import datetime
from typing import List, Optional

import markdown
from pydantic import BaseModel, ValidationInfo, field_validator


class SnippetView(BaseModel):
    """
    The object that gets passed to the views
    """

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

    @property
    def html_description(self):
        return (
            markdown.markdown(
                self.description,
                extensions=["pymdownx.extra", "pymdownx.tasklist", "sane_lists"],
            )
            if self.description
            else None
        )


class SnippetCardView(BaseModel):
    """
    The object that gets passed to the snippet card views
    """

    id: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    command_name: Optional[str] = None
    public: Optional[bool] = False
    tags: Optional[List[str]] = []
    user_id: Optional[str] = None
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

    @property
    def content_truncated(self):
        if self.content is None:
            return ""

        return self.content[:200] + "..." if len(self.content) > 200 else self.content
