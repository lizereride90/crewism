from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Bloodline, BloodlineProgress, BloodlineStage, CharacterInstance, MasteryProgress, Trainer, TrainingSession
from database.repositories import players as repo
from database.repositories.economy import add_money
from services.training_service import bloodline_available, mastery_check, training_gains
from utils.embeds import embed, error_embed


class Training(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trainers", description="List trainers")
    async def trainers(self, interaction: discord.Interaction):
        async with SessionLocal() as s:
            r = await s.execute(select(Trainer))
            rows = r.scalars().all()
        txt = "\n".join(f"{t.id}: {t.name} [{t.specialty}] {t.price} Won LV{t.req_level}+" for t in rows)
        await interaction.response.send_message(embed=embed("Trainers", txt), ephemeral=True)

    @app_commands.command(name="train", description="Train a fighter with a trainer")
    @app_commands.describe(instance_id="Your character instance id", trainer_id="Trainer id")
    async def train(self, interaction: discord.Interaction, instance_id: int, trainer_id: str):
        await interaction.response.defer(ephemeral=True)
        gid, uid = interaction.guild_id, interaction.user.id
        p = await repo.get_or_create_player(gid, uid, interaction.user.display_name)
        async with SessionLocal() as s:
            inst = await s.get(CharacterInstance, instance_id)
            if not inst or inst.guild_id != gid or inst.owner_id != uid:
                await interaction.followup.send(embed=error_embed("Not your fighter."))
                return
            tr = await s.get(Trainer, trainer_id)
            if not tr:
                await interaction.followup.send(embed=error_embed("Unknown trainer."))
                return
            if p.level < tr.req_level:
                await interaction.followup.send(embed=error_embed(f"Needs player LV{tr.req_level}."))
                return
            # one active session at a time
            r = await s.execute(select(TrainingSession).where(
                TrainingSession.guild_id == gid, TrainingSession.user_id == uid, TrainingSession.claimed == 0))
            if r.scalars().first():
                await interaction.followup.send("Finish/claim your current session first (`/claim_train`).")
                return
            s.expunge(inst)
        try:
            await add_money(gid, uid, -tr.price, "training", ref=trainer_id)
        except ValueError:
            await interaction.followup.send(embed=error_embed("Not enough Won."))
            return
        # instant short sessions for playability: duration scaled down for common trainers
        mins = max(1, min(tr.duration_min, 5 if tr.rarity == "Common" else 60))
        async with SessionLocal() as s:
            s.add(TrainingSession(guild_id=gid, user_id=uid, instance_id=instance_id,
                                  trainer_id=trainer_id, ends_at=datetime.utcnow() + timedelta(minutes=mins)))
            await s.commit()
        await interaction.followup.send(f"Training started with {tr.name} ({mins}m). Use `/claim_train` after.")

    @app_commands.command(name="claim_train", description="Claim finished training")
    async def claim_train(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gid, uid = interaction.guild_id, interaction.user.id
        async with SessionLocal() as s:
            r = await s.execute(select(TrainingSession).where(
                TrainingSession.guild_id == gid, TrainingSession.user_id == uid, TrainingSession.claimed == 0))
            sess = r.scalars().first()
            if not sess:
                await interaction.followup.send("No active session.")
                return
            if sess.ends_at > datetime.utcnow():
                left = int((sess.ends_at - datetime.utcnow()).total_seconds() // 60) + 1
                await interaction.followup.send(f"Not done yet (~{left}m left).")
                return
            tr = await s.get(Trainer, sess.trainer_id)
            inst = await s.get(CharacterInstance, sess.instance_id)
            gains = training_gains(tr.specialty if tr else "strength")
            inst.c_str += gains["str"]; inst.c_spd += gains["spd"]
            inst.c_end += gains["end"]; inst.c_tech += gains["tech"]
            inst.xp += 50
            sess.claimed = 1
            await s.commit()
        await interaction.followup.send(f"Gains: +{gains}. Fighter #{inst.id} improved.")

    @app_commands.command(name="mastery", description="Check mastery progress")
    async def mastery(self, interaction: discord.Interaction):
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        rows = []
        for m, stat in (("strength", p.p_str), ("speed", p.p_spd), ("endurance", p.p_end), ("technique", p.p_tech)):
            rows.append(f"{m}: {mastery_check(stat, p.wins)} (stat {stat}, wins {p.wins})")
        await interaction.response.send_message(embed=embed("Mastery", "\n".join(rows)), ephemeral=True)

    @app_commands.command(name="bloodline", description="View / awaken bloodline stages")
    @app_commands.describe(action="view or awaken", bloodline_id="yamazaki/gapryong/mujin/copy_line/stray")
    async def bloodline(self, interaction: discord.Interaction, action: str = "view", bloodline_id: str = "yamazaki"):
        gid, uid = interaction.guild_id, interaction.user.id
        async with SessionLocal() as s:
            bl = await s.get(Bloodline, bloodline_id)
            if not bl:
                await interaction.response.send_message(embed=error_embed("Unknown bloodline."), ephemeral=True)
                return
            stages = (await s.execute(select(BloodlineStage).where(
                BloodlineStage.bloodline_id == bloodline_id).order_by(BloodlineStage.stage))).scalars().all()
            prog = (await s.execute(select(BloodlineProgress).where(
                BloodlineProgress.guild_id == gid, BloodlineProgress.user_id == uid,
                BloodlineProgress.bloodline_id == bloodline_id))).scalar_one_or_none()
            cur = prog.stage if prog else 0
        p = await repo.get_or_create_player(gid, uid, interaction.user.display_name)
        if action == "view":
            txt = f"{bl.name}: stage {cur}/{len(stages)}\n" + "\n".join(
                f"{'✅' if x.stage <= cur else '🔒'} S{x.stage} LV{x.level_req}+ {x.name}" for x in stages)
            await interaction.response.send_message(embed=embed("Bloodline", txt), ephemeral=True)
            return
        nxt = bloodline_available([{"stage": x.stage, "level_req": x.level_req} for x in stages], p.level, cur)
        if not nxt:
            await interaction.response.send_message("No awakening available (need higher level).", ephemeral=True)
            return
        async with SessionLocal() as s:
            if prog:
                prog.stage += 1
            else:
                s.add(BloodlineProgress(guild_id=gid, user_id=uid, bloodline_id=bloodline_id, stage=1))
                # set first bloodline on player
                from database.models import Player
                r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
                row = r.scalar_one()
                if not row.bloodline_id:
                    row.bloodline_id = bloodline_id
            await s.commit()
        await interaction.response.send_message(f"Awakened {bl.name} stage {cur+1}!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Training(bot))
