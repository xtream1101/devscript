import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class UserSignUp(BaseModel):
    email: str
    password: Optional[str] = None


class UserView(BaseModel):
    email: str
    display_name: Optional[str]
    # providers: Optional[str]
    registered_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    email: str
    # TODO: Make token_type an enum
    token_type: str

    user_id: Optional[str | uuid.UUID] = None
    provider_name: Optional[str] = None
    new_email: Optional[str] = None  # Used for validation of new email

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, v):
        if v is None:
            return v
        return str(v)

    @field_validator("new_email", mode="before")
    @classmethod
    def validate_new_email(cls, v):
        if v is None:
            return v
        return v.lower().strip()
