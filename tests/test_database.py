import pytest


@pytest.mark.asyncio
async def test_db_init_and_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/seed.db")
    import database.connection as conn
    conn.reset_engine()
    await conn.init_db()
    import services.seed_service as seed
    await seed.seed_all()
    from sqlalchemy import select
    async with conn.SessionLocal() as s:
        from database.models import CharacterDefinition
        rows = (await s.execute(select(CharacterDefinition))).scalars().all()
        assert len(rows) >= 60
