from sqlalchemy import select

from database.connection import SessionLocal
from database.models import EconomyTransaction, Player


async def add_money(guild_id: int, user_id: int, amount: int, reason: str, ref: str = "") -> int:
    """Atomic balance change with ledger. Never allows negative balance."""
    if amount == 0:
        raise ValueError("amount is zero")
    async with SessionLocal() as s:
        r = await s.execute(select(Player).where(
            Player.guild_id == guild_id, Player.user_id == user_id).with_for_update())
        p = r.scalar_one_or_none()
        if not p:
            p = Player(guild_id=guild_id, user_id=user_id, name=f"Fighter-{user_id % 10000}")
            s.add(p)
            await s.flush()
        before = p.money
        after = before + amount
        if after < 0:
            raise ValueError("insufficient funds")
        p.money = after
        s.add(EconomyTransaction(guild_id=guild_id, user_id=user_id, amount=amount,
                                 before=before, after=after, reason=reason, ref=ref))
        await s.commit()
        return after
