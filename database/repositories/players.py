from datetime import datetime

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Cooldown, Player
from utils.cooldowns import utcnow


async def get_player(guild_id: int, user_id: int) -> Player | None:
    async with SessionLocal() as s:
        r = await s.execute(select(Player).where(Player.guild_id == guild_id, Player.user_id == user_id))
        return r.scalar_one_or_none()


async def get_or_create_player(guild_id: int, user_id: int, name: str = "") -> Player:
    async with SessionLocal() as s:
        r = await s.execute(select(Player).where(Player.guild_id == guild_id, Player.user_id == user_id))
        p = r.scalar_one_or_none()
        if p:
            if name and p.name != name:
                p.name = name
                await s.commit()
            # detach copy
            s.expunge(p)
            return p
        # regen energy basis
        p = Player(guild_id=guild_id, user_id=user_id, name=name or f"Fighter-{user_id % 10000}")
        s.add(p)
        await s.commit()
        await s.refresh(p)
        s.expunge(p)
        return p


async def save_player(p: Player):
    async with SessionLocal() as s:
        await s.merge(p)
        await s.commit()


async def apply_energy(p: Player, regen_per_min: float = 0.5, cap: int = 100) -> Player:
    now = utcnow()
    mins = max(0, (now - (p.energy_updated or now)).total_seconds() / 60)
    if mins >= 1:
        p.energy = max(0, min(cap, p.energy + int(mins * regen_per_min)))
        p.energy_updated = now
    return p


async def get_cooldown(guild_id: int, user_id: int, scope: str):
    async with SessionLocal() as s:
        r = await s.execute(select(Cooldown).where(
            Cooldown.guild_id == guild_id, Cooldown.user_id == user_id, Cooldown.scope == scope))
        return r.scalar_one_or_none()


async def set_cooldown(guild_id: int, user_id: int, scope: str, seconds: int):
    from datetime import timedelta

    exp = utcnow() + timedelta(seconds=seconds)
    async with SessionLocal() as s:
        r = await s.execute(select(Cooldown).where(
            Cooldown.guild_id == guild_id, Cooldown.user_id == user_id, Cooldown.scope == scope))
        c = r.scalar_one_or_none()
        if c:
            c.expires_at = exp
        else:
            s.add(Cooldown(guild_id=guild_id, user_id=user_id, scope=scope, expires_at=exp))
        await s.commit()
        return exp
