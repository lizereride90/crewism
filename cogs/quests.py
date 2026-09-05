from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Event, Player, Quest, QuestProgress
from database.repositories import players as repo
from database.repositories.economy import add_money
from utils.embeds import embed


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _week() -> str:
    return datetime.utcnow().strftime("%Y-W%W")


class Quests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="quests", description="List quests + your progress")
    async def quests(self, interaction: discord.Interaction):
        gid, uid = interaction.guild_id, interaction.user.id
        async with SessionLocal() as s:
            qs = (await s.execute(select(Quest))).scalars().all()
            lines = []
            for q in qs:
                key = _today() if q.kind == "daily" else (_week() if q.kind == "weekly" else "perm")
                pr = (await s.execute(select(QuestProgress).where(
                    QuestProgress.guild_id == gid, QuestProgress.user_id == uid,
                    QuestProgress.quest_id == q.id, QuestProgress.date_key == key))).scalar_one_or_none()
                mark = "✅" if pr and pr.completed else "•"
                lines.append(f"{mark} {q.name} [{q.kind}] — {q.description}")
        await interaction.response.send_message(embed=embed("Quests", "\n".join(lines) or "None"), ephemeral=True)

    @app_commands.command(name="claim_quest", description="Claim a completed quest")
    @app_commands.describe(quest_id="Quest id (use /quests names)")
    async def claim_quest(self, interaction: discord.Interaction, quest_id: str):
        await interaction.response.defer(ephemeral=True)
        gid, uid = interaction.guild_id, interaction.user.id
        p = await repo.get_or_create_player(gid, uid, interaction.user.display_name)
        async with SessionLocal() as s:
            q = await s.get(Quest, quest_id)
            if not q:
                r = await s.execute(select(Quest).where(Quest.name.ilike(f"%{quest_id}%")))
                q = r.scalars().first()
            if not q:
                await interaction.followup.send("Unknown quest.")
                return
            key = _today() if q.kind == "daily" else (_week() if q.kind == "weekly" else "perm")
            pr = (await s.execute(select(QuestProgress).where(
                QuestProgress.guild_id == gid, QuestProgress.user_id == uid,
                QuestProgress.quest_id == q.id, QuestProgress.date_key == key))).scalar_one_or_none()
            req = dict(q.req or {})
            ok = True
            if "level" in req and p.level < req["level"]:
                ok = False
            if "wins" in req and p.wins < req["wins"]:
                ok = False
            if "explore" in req:
                # explore tracked implicitly via wins+level for V1; require level>=2 as proxy
                if p.level < 2 and p.wins < 1:
                    ok = False
            if "crew" in req and not p.crew_id:
                ok = False
            if not ok:
                await interaction.followup.send("Requirements not met yet.")
                return
            if pr and pr.claimed:
                await interaction.followup.send("Already claimed.")
                return
            if pr:
                pr.completed = 1
                pr.claimed = 1
            else:
                s.add(QuestProgress(guild_id=gid, user_id=uid, quest_id=q.id,
                                    progress=1, completed=1, claimed=1, date_key=key))
            await s.commit()
            rw = dict(q.rewards or {})
        if rw.get("money"):
            await add_money(gid, uid, int(rw["money"]), "quest", ref=q.id)
        if rw.get("xp"):
            async with SessionLocal() as s:
                r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
                row = r.scalar_one()
                row.xp += int(rw["xp"])
                await s.commit()
        await interaction.followup.send(f"Claimed {q.name}: +{rw.get('money', 0)} Won +{rw.get('xp', 0)} XP.")

    @app_commands.command(name="events", description="Active world events")
    async def events(self, interaction: discord.Interaction):
        async with SessionLocal() as s:
            rows = (await s.execute(select(Event).where(Event.active == 1))).scalars().all()
        if not rows:
            await interaction.response.send_message("No active events. Gang war season starts soon.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed(
            "Events", "\n".join(f"{e.name}" for e in rows)), ephemeral=True)

    @app_commands.command(name="generations", description="Your generation progress")
    async def generations(self, interaction: discord.Interaction):
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        txt = (f"You are Gen {p.generation}.\nGen 2: J High streets (start).\n"
               f"Gen 1: Workers/Cheonliang at LV12+.\nGen 0: Legends at LV25+.\n"
               f"Bosses/territories gate the climb.")
        await interaction.response.send_message(embed=embed("Generations", txt), ephemeral=True)

    @app_commands.command(name="workers", description="Workers faction intel")
    async def workers(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=embed(
            "Workers", "Affiliates run Gangnam. Executives appear as bosses. "
                       "Beat them for big Won. Details configurable as canon is revealed."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Quests(bot))
