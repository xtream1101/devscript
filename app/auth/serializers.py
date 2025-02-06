import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ValidationInfo, field_validator


class UserSignUpSerializer(BaseModel):
    email: str
    password: Optional[str] = None
    confirm_password: Optional[str] = None


class UserSerializer(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    # providers: Optional[str]
    registered_at: Optional[datetime]

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    def uuid_to_str(cls, v: str, info: ValidationInfo) -> str:
        if v is None:
            return None
        return str(v)


class TokenDataSerializer(BaseModel):
    email: str
    # TODO: Make token_type an enum
    token_type: str

    user_id: Optional[str | uuid.UUID] = None
    provider_name: Optional[str] = None
    new_email: Optional[str] = None  # Used for validation of new email

    exp: Optional[datetime] = None

    @field_validator("exp", mode="before")
    @classmethod
    def validate_exp(cls, v):
        if v is None:
            return None
        return datetime.fromtimestamp(v, timezone.utc)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, v):
        if v is None:
            return None
        return str(v)

    @field_validator("new_email", mode="before")
    @classmethod
    def validate_new_email(cls, v):
        if v is None:
            return None
        return v.lower().strip()
