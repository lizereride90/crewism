from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Battle
from utils.cooldowns import utcnow


async def create_battle(guild_id: int, btype: str, p1: int, p2: int = 0, wager: int = 0) -> Battle:
    async with SessionLocal() as s:
        b = Battle(guild_id=guild_id, battle_type=btype, p1_id=p1, p2_id=p2, wager=wager)
        s.add(b)
        await s.commit()
        await s.refresh(b)
        s.expunge(b)
        return b


async def resolve_battle(battle_id: int, winner_id: int | None, log: dict):
    async with SessionLocal() as s:
        b = await s.get(Battle, battle_id)
        if not b or b.state != "active":
            return None
        b.state = "resolved"
        b.winner_id = winner_id
        b.log = log
        await s.commit()
        return b
