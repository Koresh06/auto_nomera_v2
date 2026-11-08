"""Миграции против реального Postgres: применяются с нуля и не расходятся
с ORM-моделями (то, что в проде увидел бы `alembic check`)."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.infrastructure.database.models import BaseModel


async def _diff(url: str) -> list:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        diff = await conn.run_sync(
            lambda sync_conn: compare_metadata(
                MigrationContext.configure(sync_conn), BaseModel.metadata
            )
        )
        tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    await engine.dispose()
    return diff, tables


async def test_upgrade_head_creates_every_model_table(migrated_db):
    _, tables = await _diff(migrated_db)
    assert set(BaseModel.metadata.tables) <= tables


async def test_migrated_schema_matches_models(migrated_db):
    diff, _ = await _diff(migrated_db)
    assert diff == [], f"Схема после миграций расходится с моделями: {diff}"


def test_balance_ledger_migration_rolls_back_and_reapplies(migrated_db):
    """Откат нужен на случай неудачного деплоя: enum должен удаляться вместе
    с таблицей, иначе повторный upgrade упадёт с «type already exists»."""
    from alembic import command
    from alembic.config import Config

    from src.core.config.database import PostgresSettings

    original_url = PostgresSettings.url
    PostgresSettings.url = property(lambda self: migrated_db)  # type: ignore[method-assign,assignment]
    try:
        config = Config("alembic.ini")
        command.downgrade(config, "5e1740d656ab")
        command.upgrade(config, "head")
    finally:
        PostgresSettings.url = original_url  # type: ignore[method-assign]
