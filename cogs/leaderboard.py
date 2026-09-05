import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import desc, select

from database.connection import SessionLocal
from database.models import Crew, Player


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Server rankings")
    @app_commands.describe(board="wins, money, bounty, level")
    @app_commands.choices(board=[
        app_commands.Choice(name="Most Wins", value="wins"),
        app_commands.Choice(name="Richest", value="money"),
        app_commands.Choice(name="Highest Bounty", value="bounty"),
        app_commands.Choice(name="Highest Level", value="level"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, board: str = "wins"):
        col = {"wins": Player.wins, "money": Player.money, "bounty": Player.bounty, "level": Player.level}[board]
        async with SessionLocal() as s:
            rows = (await s.execute(select(Player).where(Player.guild_id == interaction.guild_id)
                                    .order_by(desc(col)).limit(10))).scalars().all()
        if not rows:
            await interaction.response.send_message("Nobody ranked yet.", ephemeral=True)
            return
        lines = [f"{i+1}. {r.name} — {getattr(r, board):,}" for i, r in enumerate(rows)]
        await interaction.response.send_message(
            embed=discord.Embed(title=f"Leaderboard: {board}", description="\n".join(lines), color=0xFFD700))

    @app_commands.command(name="bounty", description="Check a fighter's bounty")
    async def bounty(self, interaction: discord.Interaction, member: discord.Member | None = None):
        m = member or interaction.user
        async with SessionLocal() as s:
            r = await s.execute(select(Player).where(Player.guild_id == interaction.guild_id, Player.user_id == m.id))
            p = r.scalar_one_or_none()
        if not p:
            await interaction.response.send_message("No record.", ephemeral=True)
            return
        await interaction.response.send_message(f"{p.name}: {p.bounty:,} bounty (W{p.wins}/L{p.losses}).", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
