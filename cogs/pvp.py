import random

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Player
from database.repositories import players as repo
from database.repositories.battles import create_battle, resolve_battle
from database.repositories.economy import add_money
from services import combat_service
from services.character_service import team_power
from database.repositories.characters import list_instances
from utils.embeds import embed, error_embed
from utils.permissions import clamp_amount


def _combatant(p, team_bonus: int = 0) -> dict:
    return {"name": p.name, "str": p.p_str + team_bonus // 4, "spd": p.p_spd,
            "end": p.p_end, "tech": p.p_tech, "iq": p.battle_iq,
            "style": "Street Fighting", "abilities": []}


async def _team_bonus(gid: int, uid: int) -> int:
    try:
        rows = await list_instances(gid, uid)
        mems = [{"str": r.c_str, "spd": r.c_spd, "end": r.c_end, "tech": r.c_tech,
                 "rarity": "Common", "faction": "", "style": "", "char_class": ""} for r in rows[:4]]
        return team_power(mems) // 20 if mems else 0
    except Exception:
        return 0


class Pvp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fight", description="Challenge another fighter (1v1, optional wager)")
    @app_commands.describe(opponent="Who to fight", wager="Won wager (0 = friendly)")
    async def fight(self, interaction: discord.Interaction, opponent: discord.Member, wager: int = 0):
        if opponent.id == interaction.user.id or opponent.bot:
            await interaction.response.send_message(embed=error_embed("Invalid opponent."), ephemeral=True)
            return
        await interaction.response.defer()
        await self._run_fight(interaction.guild_id, interaction.user, opponent,
                              wager, interaction.followup.send)


    @commands.command(name="fight", aliases=["challenge", "vs"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def fight_prefix(self, ctx: commands.Context, opponent: discord.Member, wager: int = 0):
        if opponent.id == ctx.author.id or opponent.bot:
            await ctx.send(embed=error_embed("Mention a real opponent. `c!fight @user 100`"))
            return
        await self._run_fight(ctx.guild.id, ctx.author, opponent, wager, ctx.send)

    async def _run_fight(self, gid, author, opponent, wager, send):
        from utils.server_config import is_enabled
        if not await is_enabled(gid, "pvp_enabled"):
            await send(embed=error_embed("PvP is disabled on this server (dashboard setting)."))
            return
        wager = clamp_amount(wager, 0, 10000) if wager else 0
        a = await repo.get_or_create_player(gid, author.id, author.display_name)
        b = await repo.get_or_create_player(gid, opponent.id, opponent.display_name)
        if wager:
            if a.money < wager or b.money < wager:
                await send(embed=error_embed("Someone can't cover the wager."))
                return
            try:
                await add_money(gid, a.user_id, -wager, "pvp_stake", ref=f"vs{b.user_id}")
                await add_money(gid, b.user_id, -wager, "pvp_stake", ref=f"vs{a.user_id}")
            except ValueError:
                try:
                    await add_money(gid, a.user_id, wager, "pvp_refund", ref="stake_fail")
                except Exception:
                    pass
                await send(embed=error_embed("Wager failed."))
                return
        ba, bb = await _team_bonus(gid, a.user_id), await _team_bonus(gid, b.user_id)
        res = combat_service.simulate(_combatant(a, ba), _combatant(b, bb), seed=random.randint(1, 999999))
        a_won = res["winner_side"] == "A"
        bt = await create_battle(gid, "ranked" if wager else "friendly", a.user_id, b.user_id, wager)
        await resolve_battle(bt.id, a.user_id if a_won else b.user_id, {"log": res["log"]})
        async with SessionLocal() as s:
            for uid, won in ((a.user_id, a_won), (b.user_id, not a_won)):
                r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
                row = r.scalar_one()
                if won:
                    row.wins += 1
                    row.bounty += 20 + wager // 100
                    row.reputation += 10
                else:
                    row.losses += 1
            await s.commit()
        if wager:
            await add_money(gid, a.user_id if a_won else b.user_id, wager * 2, "pvp_win", ref=f"battle:{bt.id}")
        lines = "\n".join(res["log"][-8:])
        winner = a.name if a_won else b.name
        await send(embed=embed(f"{winner} wins! {'(+'+str(wager*2)+' Won)' if wager else '(friendly)'}", lines,
                               color=0x57F287 if a_won else 0xED4245))


async def setup(bot):
    await bot.add_cog(Pvp(bot))
