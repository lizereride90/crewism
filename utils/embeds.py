import discord

COLORS = {
    "Common": 0x9E9E9E,
    "Uncommon": 0x4CAF50,
    "Rare": 0x2196F3,
    "Epic": 0x9C27B0,
    "Legendary": 0xFF9800,
    "Mythic": 0xF44336,
    "info": 0x2B2D31,
    "win": 0x57F287,
    "lose": 0xED4245,
}


def embed(title: str, desc: str = "", color: int = 0x2B2D31) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=color)


def rarity_color(rarity: str) -> int:
    return COLORS.get(rarity, COLORS["info"])


def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(title="Crewism", description=msg, color=COLORS["lose"])
