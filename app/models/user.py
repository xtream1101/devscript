from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy.orm import relationship

from app.models import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    snippets = relationship("Snippet", back_populates="user", cascade="all, delete")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete")
