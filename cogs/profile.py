import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Player
from database.repositories import players as repo
from database.repositories.economy import add_money
from services.economy_service import daily_reward
from utils.embeds import embed, error_embed
from utils.formatting import fmt_money, xp_for_level


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Show your Crewism fighter profile")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer()
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        p = await repo.apply_energy(p)
        await repo.save_player(p)
        need = xp_for_level(p.level)
        e = embed(f"{p.name} — LV {p.level}",
                  f"XP {p.xp}/{need} • {fmt_money(p.money)} • REP {p.reputation}\n"
                  f"STR {p.p_str} SPD {p.p_spd} END {p.p_end} TEC {p.p_tech} IQ {p.battle_iq}\n"
                  f"Gen {p.generation} • Bloodline {p.bloodline_id or 'Stray'} • Region {p.region}\n"
                  f"W {p.wins} L {p.losses} • Bounty {p.bounty:,} • Energy {p.energy}/100",
                  color=0x57F287)
        # card image offloaded so we never block the loop
        try:
            from utils import image_utils
            loop = asyncio.get_running_loop()
            path = await loop.run_in_executor(
                None, image_utils.profile_card, p.name, p.level, p.money, p.wins, p.losses)
            e.set_image(url="attachment://card.png")
            await interaction.followup.send(embed=e, file=discord.File(path, filename="card.png"))
        except Exception:
            await interaction.followup.send(embed=e)

    @app_commands.command(name="balance", description="Show money and reputation")
    async def balance(self, interaction: discord.Interaction):
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        await interaction.response.send_message(f"{fmt_money(p.money)} • REP {p.reputation}", ephemeral=True)

    @app_commands.command(name="daily", description="Claim daily allowance")
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        now = datetime.utcnow()
        if p.last_daily and (now - p.last_daily).total_seconds() < 20 * 3600:
            left = int(20 * 3600 - (now - p.last_daily).total_seconds()) // 3600 + 1
            await interaction.followup.send(f"Already claimed. Come back in ~{left}h.")
            return
        reward = daily_reward(1)
        try:
            from utils.server_config import daily_base_for
            base = await daily_base_for(interaction.guild_id)
            reward = base + min(500, 25)
        except Exception:
            pass
        # update timestamp first (idempotent-ish), then ledger money
        async with SessionLocal() as s:
            r = await s.execute(select(Player).where(
                Player.guild_id == interaction.guild_id, Player.user_id == interaction.user.id))
            row = r.scalar_one()
            row.last_daily = now
            await s.commit()
        await add_money(interaction.guild_id, interaction.user.id, reward, "daily")
        await interaction.followup.send(f"+{fmt_money(reward)} daily claimed.")

    @app_commands.command(name="stats", description="Show detailed stats")
    async def stats(self, interaction: discord.Interaction):
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        e = embed("Stats", f"STR {p.p_str}\nSPD {p.p_spd}\nEND {p.p_end}\nTEC {p.p_tech}\n"
                           f"IQ {p.battle_iq}\nTalent {p.talent}\nPotential {p.potential}")
        await interaction.response.send_message(embed=e, ephemeral=True)


    # ---- prefix mirrors (c!profile etc.) ----

    @commands.command(name="profile", aliases=["p", "me"])
    async def profile_prefix(self, ctx: commands.Context):
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        p = await repo.apply_energy(p)
        await repo.save_player(p)
        need = xp_for_level(p.level)
        e = embed(f"{p.name} — LV {p.level}",
                  f"XP {p.xp}/{need} • {fmt_money(p.money)} • REP {p.reputation}\n"
                  f"STR {p.p_str} SPD {p.p_spd} END {p.p_end} TEC {p.p_tech} IQ {p.battle_iq}\n"
                  f"Gen {p.generation} • Bloodline {p.bloodline_id or 'Stray'} • Region {p.region}\n"
                  f"W {p.wins} L {p.losses} • Bounty {p.bounty:,} • Energy {p.energy}/100",
                  color=0x57F287)
        try:
            from utils import image_utils
            loop = asyncio.get_running_loop()
            path = await loop.run_in_executor(
                None, image_utils.profile_card, p.name, p.level, p.money, p.wins, p.losses)
            e.set_image(url="attachment://card.png")
            await ctx.send(embed=e, file=discord.File(path, filename="card.png"))
        except Exception:
            await ctx.send(embed=e)

    @commands.command(name="balance", aliases=["bal", "won"])
    async def balance_prefix(self, ctx: commands.Context):
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        await ctx.send(f"{fmt_money(p.money)} • REP {p.reputation}")

    @commands.command(name="daily")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily_prefix(self, ctx: commands.Context):
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        now = datetime.utcnow()
        if p.last_daily and (now - p.last_daily).total_seconds() < 20 * 3600:
            left = int(20 * 3600 - (now - p.last_daily).total_seconds()) // 3600 + 1
            await ctx.send(f"Already claimed. Come back in ~{left}h.")
            return
        reward = daily_reward(1)
        try:
            from utils.server_config import daily_base_for
            base = await daily_base_for(ctx.guild.id)
            reward = base + min(500, 25)
        except Exception:
            pass
        async with SessionLocal() as s:
            r = await s.execute(select(Player).where(
                Player.guild_id == ctx.guild.id, Player.user_id == ctx.author.id))
            row = r.scalar_one()
            row.last_daily = now
            await s.commit()
        await add_money(ctx.guild.id, ctx.author.id, reward, "daily")
        await ctx.send(f"+{fmt_money(reward)} daily claimed.")

    @commands.command(name="stats")
    async def stats_prefix(self, ctx: commands.Context):
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        e = embed("Stats", f"STR {p.p_str}\nSPD {p.p_spd}\nEND {p.p_end}\nTEC {p.p_tech}\n"
                           f"IQ {p.battle_iq}\nTalent {p.talent}\nPotential {p.potential}")
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(Profile(bot))
