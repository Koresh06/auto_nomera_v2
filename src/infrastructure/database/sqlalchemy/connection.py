from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)

from src.core.config import settings


engine: AsyncEngine = create_async_engine(
    settings.db.db_url,
    echo=settings.db.echo,
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
