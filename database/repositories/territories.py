from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Territory, TerritoryOwnership


async def list_territories():
    async with SessionLocal() as s:
        r = await s.execute(select(Territory))
        rows = r.scalars().all()
        for x in rows:
            s.expunge(x)
        return rows


async def ownership(guild_id: int, territory_id: str):
    async with SessionLocal() as s:
        r = await s.execute(select(TerritoryOwnership).where(
            TerritoryOwnership.guild_id == guild_id, TerritoryOwnership.territory_id == territory_id))
        o = r.scalar_one_or_none()
        if o:
            s.expunge(o)
        return o
