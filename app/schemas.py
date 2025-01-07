from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserSignUp(BaseModel):
    email: str
    password: Optional[str] = None
    fullname: Optional[str] = None


class User(BaseModel):
    email: str
    fullname: Optional[str]
    provider: Optional[str]
    register_date: Optional[datetime]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class UserStat(BaseModel):
    provider: str
    count: int
