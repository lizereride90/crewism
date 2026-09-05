"""Per-server feature toggles (dashboard-controlled). Defaults to all-on."""
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import ServerConfig

_DEFAULTS = {"encounter_enabled": 1, "pvp_enabled": 1, "gambling_enabled": 1}


async def is_enabled(guild_id: int, feature: str) -> bool:
    """feature: encounter_enabled | pvp_enabled | gambling_enabled."""
    try:
        async with SessionLocal() as s:
            row = await s.get(ServerConfig, guild_id)
            if not row:
                return True
            return bool(getattr(row, feature, 1))
    except Exception:
        return True


async def get_spawn_channel(guild_id: int) -> int | None:
    try:
        async with SessionLocal() as s:
            row = await s.get(ServerConfig, guild_id)
            return row.spawn_channel if row else None
    except Exception:
        return None


async def daily_base_for(guild_id: int) -> int:
    """Dashboard-configurable daily reward base (server_config.config.daily_base)."""
    import json

    try:
        async with SessionLocal() as s:
            row = await s.get(ServerConfig, guild_id)
            if row and row.config:
                cfg = row.config if isinstance(row.config, dict) else json.loads(row.config)
                return max(0, min(10000, int(cfg.get("daily_base", 500))))
    except Exception:
        pass
    return 500
