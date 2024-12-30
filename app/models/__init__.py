from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker

from app.settings import settings

Base: DeclarativeMeta = declarative_base()

engine = create_async_engine(settings.DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Import models to register them with SQLAlchemy
from app.models.user import User  # noqa: F401
from app.models.snippet import Snippet  # noqa: F401
from app.models.api_key import APIKey  # noqa: F401
from app.models.tag import Tag  # noqa: F401
