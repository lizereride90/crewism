from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Crew, CrewMember, Player


async def get_crew(crew_id: int):
    async with SessionLocal() as s:
        c = await s.get(Crew, crew_id)
        if c:
            s.expunge(c)
        return c


async def my_crew(guild_id: int, user_id: int):
    async with SessionLocal() as s:
        p = (await s.execute(select(Player).where(
            Player.guild_id == guild_id, Player.user_id == user_id))).scalar_one_or_none()
        if not p or not p.crew_id:
            return None
        c = await s.get(Crew, p.crew_id)
        if c:
            s.expunge(c)
        return c


async def create_crew(guild_id: int, leader_id: int, name: str, tag: str = "") -> Crew:
    async with SessionLocal() as s:
        c = Crew(guild_id=guild_id, name=name.strip()[:48], tag=tag.strip()[:8], leader_id=leader_id)
        s.add(c)
        await s.flush()
        s.add(CrewMember(crew_id=c.id, guild_id=guild_id, user_id=leader_id))
        p = (await s.execute(select(Player).where(
            Player.guild_id == guild_id, Player.user_id == leader_id))).scalar_one_or_none()
        if p:
            p.crew_id = c.id
        await s.commit()
        await s.refresh(c)
        s.expunge(c)
        return c
