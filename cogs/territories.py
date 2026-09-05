import random

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Player, Territory, TerritoryOwnership
from database.repositories import players as repo
from database.repositories.battles import create_battle, resolve_battle
from database.repositories.economy import add_money
from services import combat_service
from services.crew_service import can_conquer, next_conquest_time
from utils.embeds import embed, error_embed


class Territories(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="territories", description="List Seoul territories + owners")
    async def territories(self, interaction: discord.Interaction):
        async with SessionLocal() as s:
            terrs = (await s.execute(select(Territory))).scalars().all()
            lines = []
            for t in terrs:
                o = (await s.execute(select(TerritoryOwnership).where(
                    TerritoryOwnership.guild_id == interaction.guild_id,
                    TerritoryOwnership.territory_id == t.id))).scalar_one_or_none()
                owner = (o.owner_type if o else "npc") + (f" crew#{o.crew_id}" if o and o.crew_id else "")
                lines.append(f"{t.name} (LV{t.rec_level}+) — {owner} — {t.income:,}/day")
        await interaction.response.send_message(embed=embed("Seoul", "\n".join(lines)), ephemeral=True)

    @app_commands.command(name="conquer", description="Fight the defenders to take a territory")
    @app_commands.describe(territory="Territory id or name part")
    async def conquer(self, interaction: discord.Interaction, territory: str):
        await interaction.response.defer()
        gid, uid = interaction.guild_id, interaction.user.id
        p = await repo.get_or_create_player(gid, uid, interaction.user.display_name)
        async with SessionLocal() as s:
            r = await s.execute(select(Territory))
            all_t = r.scalars().all()
            t = next((x for x in all_t if x.id == territory or territory.lower() in x.name.lower()), None)
            if not t:
                await interaction.followup.send(embed=error_embed("Unknown territory."))
                return
            s.expunge(t)
            o = (await s.execute(select(TerritoryOwnership).where(
                TerritoryOwnership.guild_id == gid, TerritoryOwnership.territory_id == t.id))).scalar_one_or_none()
            if o and not can_conquer(o.cooldown_until):
                await interaction.followup.send(embed=error_embed("Territory is under conquest cooldown."))
                return
            if p.level < t.rec_level:
                await interaction.followup.send(embed=error_embed(f"Needs LV{t.rec_level}."))
                return
        # defender scales with territory
        dfn = {"name": f"{t.name} defenders", "str": 14 + t.rec_level, "spd": 12 + t.rec_level,
               "end": 14 + t.rec_level, "tech": 12 + t.rec_level, "iq": 12,
               "style": "Street Fighting", "abilities": []}
        atk = {"name": p.name, "str": p.p_str, "spd": p.p_spd, "end": p.p_end,
               "tech": p.p_tech, "iq": p.battle_iq, "style": "Street Fighting", "abilities": []}
        res = combat_service.simulate(atk, dfn, seed=random.randint(1, 999999))
        won = res["winner_side"] == "A"
        bt = await create_battle(gid, "territory", uid)
        await resolve_battle(bt.id, uid if won else 0, {"log": res["log"]})
        lines = "\n".join(res["log"][-8:])
        if not won:
            async with SessionLocal() as s:
                r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
                r.scalar_one().losses += 1
                await s.commit()
            await interaction.followup.send(embed=embed(f"Repelled at {t.name}", lines, color=0xED4245))
            return
        async with SessionLocal() as s:
            o = (await s.execute(select(TerritoryOwnership).where(
                TerritoryOwnership.guild_id == gid, TerritoryOwnership.territory_id == t.id))).scalar_one_or_none()
            if not o:
                o = TerritoryOwnership(guild_id=gid, territory_id=t.id)
                s.add(o)
            # owner: crew if in crew else player
            r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
            row = r.scalar_one()
            row.wins += 1
            row.reputation += 30
            if row.crew_id:
                o.owner_type = "crew"
                o.crew_id = row.crew_id
            else:
                o.owner_type = "player"
                o.crew_id = None
            o.cooldown_until = next_conquest_time()
            await s.commit()
        await add_money(gid, uid, t.income, "conquest", ref=t.id)
        await interaction.followup.send(embed=embed(f"Took {t.name}! +{t.income:,} Won", lines))


async def setup(bot):
    await bot.add_cog(Territories(bot))
