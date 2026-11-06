# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Base


class Database:
    def __init__(self, url: str, echo: bool = False):
        kwargs: dict = {"echo": echo}
        if ":memory:" in url or url.rstrip("/").endswith("sqlite+aiosqlite:"):
            # a single shared connection, otherwise every session would see its own empty database
            kwargs.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
        elif not url.startswith("sqlite"):
            kwargs.update(pool_pre_ping=True)
        self.engine: AsyncEngine = create_async_engine(url, **kwargs)
        self._maker = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """A session that commits on success and rolls back on error."""
        async with self._maker() as s:
            try:
                yield s
                await s.commit()
            except BaseException:
                await s.rollback()
                raise

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()
