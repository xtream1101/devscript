from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.settings import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    echo=False,
    poolclass=NullPool,  # Disable connection pooling to prevent stale connections
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session_maker()
    try:
        yield session
    finally:
        await session.close()
