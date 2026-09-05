import random

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Boss, BossAttempt, CharacterDefinition, Player
from database.repositories import players as repo
from database.repositories.battles import create_battle, resolve_battle
from database.repositories.economy import add_money
from services import combat_service
from services.crew_service import boss_phases_triggered
from utils.cooldowns import on_cooldown
from utils.embeds import embed, error_embed
from utils.formatting import fmt_money


class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bosses", description="List bosses")
    async def bosses(self, interaction: discord.Interaction):
        async with SessionLocal() as s:
            r = await s.execute(select(Boss))
            rows = r.scalars().all()
        txt = "\n".join(f"{b.name} LV{b.level} ({b.region})" for b in rows)
        await interaction.response.send_message(embed=embed("Bosses", txt), ephemeral=True)

    @app_commands.command(name="boss", description="Fight a boss (phases, cooldowns)")
    @app_commands.describe(boss_id="Boss id, see /bosses names")
    async def boss(self, interaction: discord.Interaction, boss_id: str):
        await interaction.response.defer()
        gid, uid = interaction.guild_id, interaction.user.id
        p = await repo.get_or_create_player(gid, uid, interaction.user.display_name)
        async with SessionLocal() as s:
            b = await s.get(Boss, boss_id)
            if not b:
                # fuzzy by name
                r = await s.execute(select(Boss).where(Boss.name.ilike(f"%{boss_id}%")))
                b = r.scalars().first()
            if not b:
                await interaction.followup.send(embed=error_embed("Unknown boss."))
                return
            s.expunge(b)
            # cooldown: last attempt
            r = await s.execute(select(BossAttempt).where(
                BossAttempt.guild_id == gid, BossAttempt.user_id == uid,
                BossAttempt.boss_id == b.id).order_by(BossAttempt.attempted_at.desc()))
            last = r.scalars().first()
            from datetime import datetime, timedelta
            if last and datetime.utcnow() - last.attempted_at < timedelta(hours=b.cooldown_h):
                await interaction.followup.send(embed=error_embed(f"On cooldown ({b.cooldown_h}h)."))
                return
            if p.level < max(1, b.level - 8):
                await interaction.followup.send(embed=error_embed(f"Too strong. Recommended LV{b.level}."))
                return

        a = {"name": p.name, "str": p.p_str, "spd": p.p_spd, "end": p.p_end,
             "tech": p.p_tech, "iq": p.battle_iq, "style": "Street Fighting", "abilities": []}
        st = b.stats or {}
        bb = {"name": b.name, "str": st.get("str", 20), "spd": st.get("spd", 20),
              "end": st.get("end", 20), "tech": st.get("tech", 20), "iq": st.get("iq", 15),
              "style": "Street Fighting", "abilities": list(b.abilities or [])}
        res = combat_service.simulate(a, bb, seed=random.randint(1, 999999))
        won = res["winner_side"] == "A"
        bt = await create_battle(gid, "boss", uid)
        await resolve_battle(bt.id, uid if won else 0, {"log": res["log"]})
        async with SessionLocal() as s:
            s.add(BossAttempt(guild_id=gid, user_id=uid, boss_id=b.id, won=1 if won else 0))
            r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
            row = r.scalar_one()
            if won:
                row.wins += 1
            else:
                row.losses += 1
            await s.commit()
        lines = "\n".join(res["log"][-10:])
        phases = boss_phases_triggered(list(b.phases or []), 0.3 if won else 0.8)
        extra = ("\nPhases: " + "; ".join(x.get("note", "") for x in phases)) if phases else ""
        if won:
            rw = (b.rewards or {})
            await add_money(gid, uid, int(rw.get("money", 500)), "boss", ref=b.id)
            async with SessionLocal() as s:
                r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
                row = r.scalar_one()
                row.xp += int(rw.get("xp", 300))
                row.reputation += 50
                await s.commit()
            await interaction.followup.send(embed=embed(f"Defeated {b.name}! +{fmt_money(rw.get('money', 0))}", lines + extra))
        else:
            await interaction.followup.send(embed=embed(f"Fell to {b.name}", lines + extra, color=0xED4245))


    # ---- prefix mirrors ----

    @commands.command(name="bosses")
    async def bosses_prefix(self, ctx: commands.Context):
        async with SessionLocal() as s:
            r = await s.execute(select(Boss))
            rows = r.scalars().all()
        txt = "\n".join(f"{b.name} LV{b.level} ({b.region})" for b in rows)
        await ctx.send(embed=embed("Bosses", txt))

    @commands.command(name="boss")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def boss_prefix(self, ctx: commands.Context, *, boss_id: str):
        gid, uid = ctx.guild.id, ctx.author.id
        p = await repo.get_or_create_player(gid, uid, ctx.author.display_name)
        async with SessionLocal() as s:
            b = await s.get(Boss, boss_id)
            if not b:
                r = await s.execute(select(Boss).where(Boss.name.ilike(f"%{boss_id}%")))
                b = r.scalars().first()
            if not b:
                await ctx.send(embed=error_embed("Unknown boss."))
                return
            s.expunge(b)
            r = await s.execute(select(BossAttempt).where(
                BossAttempt.guild_id == gid, BossAttempt.user_id == uid,
                BossAttempt.boss_id == b.id).order_by(BossAttempt.attempted_at.desc()))
            last = r.scalars().first()
            from datetime import datetime, timedelta
            if last and datetime.utcnow() - last.attempted_at < timedelta(hours=b.cooldown_h):
                await ctx.send(embed=error_embed(f"On cooldown ({b.cooldown_h}h)."))
                return
            if p.level < max(1, b.level - 8):
                await ctx.send(embed=error_embed(f"Too strong. Recommended LV{b.level}."))
                return
        a = {"name": p.name, "str": p.p_str, "spd": p.p_spd, "end": p.p_end,
             "tech": p.p_tech, "iq": p.battle_iq, "style": "Street Fighting", "abilities": []}
        st = b.stats or {}
        bb = {"name": b.name, "str": st.get("str", 20), "spd": st.get("spd", 20),
              "end": st.get("end", 20), "tech": st.get("tech", 20), "iq": st.get("iq", 15),
              "style": "Street Fighting", "abilities": list(b.abilities or [])}
        res = combat_service.simulate(a, bb, seed=random.randint(1, 999999))
        won = res["winner_side"] == "A"
        bt = await create_battle(gid, "boss", uid)
        await resolve_battle(bt.id, uid if won else 0, {"log": res["log"]})
        async with SessionLocal() as s:
            s.add(BossAttempt(guild_id=gid, user_id=uid, boss_id=b.id, won=1 if won else 0))
            r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
            row = r.scalar_one()
            row.wins += 1 if won else 0
            row.losses += 0 if won else 1
            await s.commit()
        lines = "\n".join(res["log"][-10:])
        if won:
            rw = (b.rewards or {})
            await add_money(gid, uid, int(rw.get("money", 500)), "boss", ref=b.id)
            async with SessionLocal() as s:
                r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
                row = r.scalar_one()
                row.xp += int(rw.get("xp", 300))
                row.reputation += 50
                await s.commit()
            await ctx.send(embed=embed(f"Defeated {b.name}! +{fmt_money(rw.get('money', 0))}", lines))
        else:
            await ctx.send(embed=embed(f"Fell to {b.name}", lines, color=0xED4245))


async def setup(bot):
    await bot.add_cog(Combat(bot))
