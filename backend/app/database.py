from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Auto-migrate: add personality column if upgrading from older schema
    async with engine.connect() as conn:
        try:
            await conn.exec_driver_sql(
                "ALTER TABLE characters ADD COLUMN personality TEXT"
            )
            await conn.commit()
        except Exception:
            pass  # Column already exists — safe to ignore
