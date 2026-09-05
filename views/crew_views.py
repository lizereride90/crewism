import discord


def crew_embed(name: str, tag: str, level: int, rep: int, treasury: int, members: int) -> discord.Embed:
    return discord.Embed(
        title=f"[{tag}] {name}" if tag else name,
        description=f"LV {level} • REP {rep} • Treasury {treasury:,} Won • {members} members",
        color=0x57F287,
    )


def territory_embed(name: str, owner: str, income: int, rec: int) -> discord.Embed:
    return discord.Embed(title=name, description=f"Owner: {owner} • Income: {income:,} Won • Rec LV {rec}",
                         color=0x2196F3)
