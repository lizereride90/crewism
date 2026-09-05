import os
from dataclasses import dataclass


@dataclass
class Settings:
    token: str = ""
    database_url: str = "sqlite+aiosqlite:///crewism.db"
    log_level: str = "INFO"
    command_guild_id: int | None = None
    image_cache_dir: str = "assets/generated"


def load_settings() -> Settings:
    from dotenv import load_dotenv
    load_dotenv()
    gid = os.getenv("COMMAND_GUILD_ID", "").strip()
    return Settings(
        token=os.getenv("DISCORD_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///crewism.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        command_guild_id=int(gid) if gid.isdigit() else None,
        image_cache_dir=os.getenv("IMAGE_CACHE_DIR", "assets/generated"),
    )


settings = load_settings()
