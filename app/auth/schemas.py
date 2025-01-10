from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserSignUp(BaseModel):
    email: str
    password: Optional[str] = None


class User(BaseModel):
    email: str
    display_name: Optional[str]
    # providers: Optional[str]
    registered_at: Optional[datetime]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
