from sqlalchemy import func, select

from database.connection import SessionLocal
from database.models import CharacterDefinition, CharacterInstance, Team, TeamMember


async def list_defs(limit: int = 200):
    async with SessionLocal() as s:
        r = await s.execute(select(CharacterDefinition).limit(limit))
        return r.scalars().all()


async def get_def(def_id: str):
    async with SessionLocal() as s:
        return await s.get(CharacterDefinition, def_id)


async def count_instances(guild_id: int, owner_id: int) -> int:
    async with SessionLocal() as s:
        r = await s.execute(select(func.count()).select_from(CharacterInstance).where(
            CharacterInstance.guild_id == guild_id, CharacterInstance.owner_id == owner_id))
        return r.scalar_one()


async def add_instance(guild_id: int, owner_id: int, def_id: str, stats: dict | None = None) -> CharacterInstance:
    stats = stats or {}
    async with SessionLocal() as s:
        d = await s.get(CharacterDefinition, def_id)
        if not d:
            raise ValueError("unknown character")
        inst = CharacterInstance(
            guild_id=guild_id, owner_id=owner_id, def_id=def_id,
            c_str=stats.get("str", d.base_str), c_spd=stats.get("spd", d.base_spd),
            c_end=stats.get("end", d.base_end), c_tech=stats.get("tech", d.base_tech),
        )
        s.add(inst)
        await s.commit()
        await s.refresh(inst)
        s.expunge(inst)
        return inst


async def list_instances(guild_id: int, owner_id: int):
    async with SessionLocal() as s:
        r = await s.execute(select(CharacterInstance).where(
            CharacterInstance.guild_id == guild_id, CharacterInstance.owner_id == owner_id
        ).order_by(CharacterInstance.level.desc(), CharacterInstance.id))
        rows = r.scalars().all()
        for x in rows:
            s.expunge(x)
        return rows


async def get_active_team(guild_id: int, owner_id: int) -> Team | None:
    async with SessionLocal() as s:
        r = await s.execute(select(Team).where(
            Team.guild_id == guild_id, Team.owner_id == owner_id, Team.is_active == 1))
        t = r.scalar_one_or_none()
        if t:
            s.expunge(t)
        return t


async def ensure_team(guild_id: int, owner_id: int) -> Team:
    t = await get_active_team(guild_id, owner_id)
    if t:
        return t
    async with SessionLocal() as s:
        t = Team(guild_id=guild_id, owner_id=owner_id, name="Main", is_active=1)
        s.add(t)
        await s.commit()
        await s.refresh(t)
        s.expunge(t)
        return t


async def team_members(team_id: int):
    async with SessionLocal() as s:
        r = await s.execute(select(TeamMember).where(TeamMember.team_id == team_id).order_by(TeamMember.slot))
        rows = r.scalars().all()
        for x in rows:
            s.expunge(x)
        return rows


async def set_team(team_id: int, instance_ids: list[int]):
    async with SessionLocal() as s:
        old = (await s.execute(select(TeamMember).where(TeamMember.team_id == team_id))).scalars().all()
        for o in old:
            await s.delete(o)
        for i, iid in enumerate(instance_ids[:4]):
            s.add(TeamMember(team_id=team_id, instance_id=iid, slot=i))
        await s.commit()
