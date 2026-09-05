from sqlalchemy import select

from database.connection import SessionLocal
from database.models import InventoryItem, ItemDefinition


async def get_item_def(item_id: str):
    async with SessionLocal() as s:
        return await s.get(ItemDefinition, item_id)


async def add_item(guild_id: int, owner_id: int, item_id: str, qty: int = 1):
    if qty <= 0:
        raise ValueError("qty must be positive")
    async with SessionLocal() as s:
        r = await s.execute(select(InventoryItem).where(
            InventoryItem.guild_id == guild_id, InventoryItem.owner_id == owner_id,
            InventoryItem.item_id == item_id, InventoryItem.equipped_to.is_(None)))
        row = r.scalar_one_or_none()
        if row:
            row.qty += qty
        else:
            s.add(InventoryItem(guild_id=guild_id, owner_id=owner_id, item_id=item_id, qty=qty))
        await s.commit()


async def remove_item(guild_id: int, owner_id: int, item_id: str, qty: int = 1):
    async with SessionLocal() as s:
        r = await s.execute(select(InventoryItem).where(
            InventoryItem.guild_id == guild_id, InventoryItem.owner_id == owner_id,
            InventoryItem.item_id == item_id, InventoryItem.equipped_to.is_(None)))
        row = r.scalar_one_or_none()
        if not row or row.qty < qty:
            raise ValueError("not enough items")
        row.qty -= qty
        if row.qty <= 0:
            await s.delete(row)
        await s.commit()


async def list_inventory(guild_id: int, owner_id: int):
    async with SessionLocal() as s:
        r = await s.execute(select(InventoryItem).where(
            InventoryItem.guild_id == guild_id, InventoryItem.owner_id == owner_id))
        rows = r.scalars().all()
        for x in rows:
            s.expunge(x)
        return rows
