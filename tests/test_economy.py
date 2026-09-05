import pytest

from database.connection import SessionLocal, init_db
from database.repositories.economy import add_money
from database.repositories.players import get_or_create_player


@pytest.mark.asyncio
async def test_negative_balance_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/t.db")
    import database.connection as conn
    conn.reset_engine()
    await init_db()
    await get_or_create_player(1, 111, "T")
    with pytest.raises(ValueError):
        await add_money(1, 111, -100000, "test")


@pytest.mark.asyncio
async def test_ledger_positive(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/t2.db")
    import database.connection as conn
    conn.reset_engine()
    await init_db()
    await get_or_create_player(1, 222, "T2")
    bal = await add_money(1, 222, 100, "test")
    assert bal >= 600
