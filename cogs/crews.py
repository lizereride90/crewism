import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select

from database.connection import SessionLocal
from database.models import Crew, CrewMember, Player
from database.repositories import players as repo
from database.repositories.crews import create_crew, get_crew, my_crew
from services.crew_service import crew_war_power
from services.character_service import team_power
from database.repositories.characters import list_instances
from database.repositories.battles import create_battle, resolve_battle
from utils.embeds import embed, error_embed
from utils.permissions import is_valid_name
from views.crew_views import crew_embed


class Crews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    crew = app_commands.Group(name="crew", description="Crew commands")

    @crew.command(name="create", description="Found your own crew")
    @app_commands.describe(name="Crew name", tag="Short tag")
    async def create(self, interaction: discord.Interaction, name: str, tag: str = ""):
        if not is_valid_name(name, 48):
            await interaction.response.send_message(embed=error_embed("Bad crew name."), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        if p.crew_id:
            await interaction.followup.send("Already in a crew. Leave first.")
            return
        try:
            c = await create_crew(interaction.guild_id, interaction.user.id, name, tag)
        except Exception:
            await interaction.followup.send(embed=error_embed("Name taken."))
            return
        await interaction.followup.send(embed=crew_embed(c.name, c.tag, c.level, 0, 0, 1))

    @crew.command(name="info", description="Show your crew")
    async def info(self, interaction: discord.Interaction):
        c = await my_crew(interaction.guild_id, interaction.user.id)
        if not c:
            await interaction.response.send_message("No crew. `/crew create` or `/crew join`.", ephemeral=True)
            return
        async with SessionLocal() as s:
            n = (await s.execute(select(func.count()).select_from(CrewMember).where(CrewMember.crew_id == c.id))).scalar_one()
        await interaction.response.send_message(
            embed=crew_embed(c.name, c.tag, c.level, c.reputation, c.treasury, n), ephemeral=True)

    @crew.command(name="join", description="Join a crew by name")
    async def join(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        async with SessionLocal() as s:
            r = await s.execute(select(Crew).where(Crew.guild_id == interaction.guild_id, Crew.name.ilike(name)))
            c = r.scalars().first()
            if not c:
                await interaction.followup.send("No such crew.")
                return
            cid = c.id
            # already in one?
            r = await s.execute(select(Player).where(Player.guild_id == interaction.guild_id,
                                                     Player.user_id == interaction.user.id))
            pl = r.scalar_one_or_none()
            if pl and pl.crew_id:
                await interaction.followup.send("Leave your crew first.")
                return
            s.add(CrewMember(crew_id=cid, guild_id=interaction.guild_id, user_id=interaction.user.id))
            if pl:
                pl.crew_id = cid
            await s.commit()
        await interaction.followup.send(f"Joined crew #{cid}.")

    @crew.command(name="leave", description="Leave your crew")
    async def leave(self, interaction: discord.Interaction):
        async with SessionLocal() as s:
            r = await s.execute(select(Player).where(Player.guild_id == interaction.guild_id,
                                                     Player.user_id == interaction.user.id))
            pl = r.scalar_one_or_none()
            if not pl or not pl.crew_id:
                await interaction.response.send_message("Not in a crew.", ephemeral=True)
                return
            cid = pl.crew_id
            pl.crew_id = None
            m = (await s.execute(select(CrewMember).where(CrewMember.crew_id == cid,
                                                          CrewMember.user_id == interaction.user.id))).scalar_one_or_none()
            if m:
                await s.delete(m)
            await s.commit()
        await interaction.response.send_message("Left crew.", ephemeral=True)

    @crew.command(name="war", description="Crew war vs another crew (leader only, team power)")
    @app_commands.describe(enemy="Enemy crew name")
    async def war(self, interaction: discord.Interaction, enemy: str):
        await interaction.response.defer()
        mine = await my_crew(interaction.guild_id, interaction.user.id)
        if not mine or mine.leader_id != interaction.user.id:
            await interaction.followup.send(embed=error_embed("Only crew leaders can declare war."))
            return
        async with SessionLocal() as s:
            r = await s.execute(select(Crew).where(Crew.guild_id == interaction.guild_id, Crew.name.ilike(enemy)))
            foe = r.scalars().first()
            if not foe or foe.id == mine.id:
                await interaction.followup.send(embed=error_embed("Enemy not found."))
                return
            s.expunge(foe)
            # gather member powers (top 3 members each)
            def _members(cid: int):
                return s.execute(select(CrewMember).where(CrewMember.crew_id == cid))

        async def power_of(cid: int) -> int:
            async with SessionLocal() as s2:
                mems = (await s2.execute(select(CrewMember).where(CrewMember.crew_id == cid).limit(3))).scalars().all()
            powers = []
            for m in mems:
                p = await repo.get_or_create_player(interaction.guild_id, m.user_id, "")
                rows = await list_instances(interaction.guild_id, m.user_id)
                tp = team_power([{"str": r.c_str, "spd": r.c_spd, "end": r.c_end, "tech": r.c_tech,
                                  "rarity": "Common", "faction": "", "style": "", "char_class": ""} for r in rows[:4]])
                powers.append(p.p_str + p.p_spd + p.p_end + p.p_tech + tp // 10)
            return crew_war_power(powers) if powers else 0

        import random
        mp, fp = await power_of(mine.id), await power_of(foe.id)
        mp += random.randint(-50, 50)
        fp += random.randint(-50, 50)
        mine_won = mp >= fp
        bt = await create_battle(interaction.guild_id, "crew_war", mine.id, foe.id)
        await resolve_battle(bt.id, mine.id if mine_won else foe.id, {"mp": mp, "fp": fp})
        async with SessionLocal() as s:
            for cid, won in ((mine.id, mine_won), (foe.id, not mine_won)):
                c = await s.get(Crew, cid)
                if won:
                    c.wins += 1
                    c.reputation += 100
                else:
                    c.losses += 1
            await s.commit()
        await interaction.followup.send(embed=embed(
            f"{mine.name} {'WINS' if mine_won else 'LOSES'} vs {foe.name}", f"Power {mp} vs {fp}"))


async def setup(bot):
    await bot.add_cog(Crews(bot))
