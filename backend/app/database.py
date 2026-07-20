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
    # Auto-migrate: add new columns for schema upgrades
    async with engine.connect() as conn:
        migrations = [
            "ALTER TABLE characters ADD COLUMN personality TEXT",
            "ALTER TABLE characters ADD COLUMN age_group VARCHAR(10)",
            "ALTER TABLE observations ADD COLUMN vocabulary_semantic INTEGER",
            "ALTER TABLE observations ADD COLUMN vocabulary_semantic_examples TEXT",
            "ALTER TABLE observations ADD COLUMN sentence_fluency INTEGER",
            "ALTER TABLE observations ADD COLUMN sentence_fluency_examples TEXT",
            "ALTER TABLE observations ADD COLUMN narrative_completeness INTEGER",
            "ALTER TABLE observations ADD COLUMN narrative_structure_note TEXT",
            "ALTER TABLE observations ADD COLUMN character_empathy INTEGER",
            "ALTER TABLE observations ADD COLUMN character_empathy_examples TEXT",
            "ALTER TABLE observations ADD COLUMN creative_initiative INTEGER",
            "ALTER TABLE observations ADD COLUMN creative_initiative_examples TEXT",
        ]
        for sql in migrations:
            try:
                await conn.exec_driver_sql(sql)
                await conn.commit()
            except Exception:
                pass  # Column already exists
