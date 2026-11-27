"""The list query is backed by a real keyset index."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(str(settings.database_url))
    yield engine
    await engine.dispose()


async def _index_defs(engine: AsyncEngine, table: str) -> dict[str, str]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "select indexname, indexdef from pg_indexes "
                "where schemaname = 'public' and tablename = :table"
            ),
            {"table": table},
        )
        return dict(rows.all())


async def test_partners_has_a_keyset_index(engine: AsyncEngine) -> None:
    definition = (await _index_defs(engine, "partners"))["ix_partners_created_at_id"]

    assert definition.endswith("(created_at DESC, id DESC)")
