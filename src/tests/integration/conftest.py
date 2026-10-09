"""Интеграционные тесты против настоящего PostgreSQL 16 (как в проде).

Postgres поднимается встроенным пакетом ``pgserver`` (бинарники из wheel,
без docker), схема создаётся реальными alembic-миграциями — так тесты
заодно проверяют, что миграции применяются с нуля и совпадают с моделями.
"""

import tempfile
from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

pgserver = pytest.importorskip("pgserver")

TEST_DB = "auto_nomera_test"


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    data_dir = tempfile.mkdtemp(prefix="auto_nomera_pg_")
    server = pgserver.get_server(data_dir, cleanup_mode="delete")
    server.psql(f"CREATE DATABASE {TEST_DB};")
    socket_dir = server.get_uri().split("host=")[-1]
    yield f"postgresql+asyncpg://postgres@/{TEST_DB}?host={socket_dir}"
    server.cleanup()


@pytest.fixture(scope="session")
def migrated_db(pg_url: str) -> str:
    """Применяет все alembic-миграции к пустой БД (upgrade head)."""
    from alembic import command
    from alembic.config import Config

    from src.core.config.database import PostgresSettings

    original_url = PostgresSettings.url
    PostgresSettings.url = property(lambda self: pg_url)  # type: ignore[method-assign,assignment]
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        PostgresSettings.url = original_url  # type: ignore[method-assign]
    return pg_url


_TABLES = (
    "publication_services, publications, slot_bookings, slot_converted, "
    "payments, ads, users, service_definitions, regions"
)


@pytest.fixture(autouse=True)
async def _clean_db(migrated_db: str) -> AsyncIterator[None]:
    yield
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    await engine.dispose()


@pytest.fixture
async def session(migrated_db: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
    await engine.dispose()


@pytest.fixture
def session_factory(migrated_db: str):
    """Фабрика независимых сессий — для проверок «другим соединением»
    (то, что реально закоммичено) и для тестов конкурентного доступа."""
    engine = create_async_engine(migrated_db, poolclass=NullPool)

    def make() -> AsyncSession:
        return AsyncSession(engine, expire_on_commit=False)

    return make
