import discord


def char_embed(name: str, rarity: str, style: str, faction: str, power: int, desc: str = "") -> discord.Embed:
    from utils.embeds import rarity_color

    e = discord.Embed(title=f"{name} [{rarity}]", description=desc or f"{style} • {faction} • POW {power}",
                      color=rarity_color(rarity))
    return e
