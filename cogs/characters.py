import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import CharacterDefinition, CharacterInstance
from database.repositories import players as repo
from database.repositories.characters import ensure_team, get_active_team, list_instances, set_team, team_members
from utils.embeds import embed, error_embed
from views.pagination import PagedEmbed, chunk


class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="collection", description="Show your recruited fighters")
    async def collection(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await list_instances(interaction.guild_id, interaction.user.id)
        if not rows:
            await interaction.followup.send("Empty. Go `/explore` and recruit.")
            return
        async with SessionLocal() as s:
            pages = []
            for part in chunk(rows, 8):
                lines = []
                for inst in part:
                    d = await s.get(CharacterDefinition, inst.def_id)
                    lines.append(f"#{inst.id} {d.name} [{d.rarity}] LV{inst.level} ({d.style})")
                pages.append(embed("Collection", "\n".join(lines)))
            await interaction.followup.send(embed=pages[0],
                view=PagedEmbed(pages, interaction.user.id) if len(pages) > 1 else None)

    @app_commands.command(name="team", description="View or set your active team (up to 4)")
    @app_commands.describe(ids="Comma-separated instance IDs, e.g. 3,5,6. Empty = view.")
    async def team(self, interaction: discord.Interaction, ids: str = ""):
        await interaction.response.defer(ephemeral=True)
        gid, uid = interaction.guild_id, interaction.user.id
        t = await ensure_team(gid, uid)
        if not ids.strip():
            mems = await team_members(t.id)
            if not mems:
                await interaction.followup.send("Team empty. `/collection` for IDs, then `/team ids:3,5`.")
                return
            async with SessionLocal() as s:
                lines = []
                for m in mems:
                    inst = await s.get(CharacterInstance, m.instance_id)
                    d = await s.get(CharacterDefinition, inst.def_id) if inst else None
                    if d:
                        lines.append(f"Slot {m.slot+1}: {d.name} LV{inst.level}")
                await interaction.followup.send(embed=embed(f"Team {t.name}", "\n".join(lines)))
            return
        try:
            wanted = [int(x.strip()) for x in ids.split(",") if x.strip()][:4]
        except ValueError:
            await interaction.followup.send(embed=error_embed("IDs must be numbers."))
            return
        # validate ownership
        owned = {r.id for r in await list_instances(gid, uid)}
        if not set(wanted) <= owned:
            await interaction.followup.send(embed=error_embed("Some IDs aren't yours."))
            return
        await set_team(t.id, wanted)
        await interaction.followup.send(f"Team set: {wanted}")

    @app_commands.command(name="dex", description="Look up a fighter")
    @app_commands.describe(name="Part of the name")
    async def dex(self, interaction: discord.Interaction, name: str):
        async with SessionLocal() as s:
            r = await s.execute(select(CharacterDefinition).where(CharacterDefinition.name.ilike(f"%{name}%")).limit(10))
            rows = r.scalars().all()
        if not rows:
            await interaction.response.send_message("No match.", ephemeral=True)
            return
        txt = "\n".join(f"{d.name} [{d.rarity}] {d.style} • {d.faction} • Gen{d.generation} • {d.role}" for d in rows)
        await interaction.response.send_message(embed=embed("Dex", txt), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Characters(bot))
