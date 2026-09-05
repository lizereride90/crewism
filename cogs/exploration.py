import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import CharacterDefinition
from database.repositories import players as repo
from database.repositories.characters import add_instance
from database.repositories.economy import add_money
from database.repositories.battles import create_battle, resolve_battle
from services import combat_service, encounter_service
from services.character_service import recruit_chance
from utils.embeds import embed, error_embed
from utils.formatting import fmt_money, power_score
from views.combat_views import EncounterView


def _player_combatant(p) -> dict:
    return {"name": p.name, "str": p.p_str, "spd": p.p_spd, "end": p.p_end,
            "tech": p.p_tech, "iq": p.battle_iq, "style": "Street Fighting",
            "abilities": [], "fatigue": max(0, 100 - p.energy) // 4}


def _def_combatant(d: CharacterDefinition, scale: float = 1.0) -> dict:
    return {"name": d.name, "str": int(d.base_str * scale), "spd": int(d.base_spd * scale),
            "end": int(d.base_end * scale), "tech": int(d.base_tech * scale),
            "iq": d.base_iq, "style": d.style,
            "abilities": [d.ability_id] if d.ability_id else [], "bloodline": d.bloodline}


class Exploration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="explore", description="Patrol your region for encounters")
    async def explore(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gid, uid = interaction.guild_id, interaction.user.id
        p = await repo.get_or_create_player(gid, uid, interaction.user.display_name)
        p = await repo.apply_energy(p)
        if p.energy < 10:
            await interaction.followup.send(embed=error_embed("Exhausted. Rest or use Choco Milk."))
            return
        # energy cost
        async with SessionLocal() as s:
            from database.models import Player
            r = await s.execute(select(Player).where(Player.guild_id == gid, Player.user_id == uid))
            row = r.scalar_one()
            row.energy = max(0, row.energy - 10)
            from utils.cooldowns import utcnow
            row.energy_updated = utcnow()
            await s.commit()
        p.energy -= 10

        enc = encounter_service.roll_encounter(p.region, p.level)
        kind = enc["kind"]

        if kind == "nothing":
            await interaction.followup.send(embed=embed("Quiet streets", "Nothing happens. The city watches."))
            return
        if kind == "money":
            amt = random.randint(50, 250)
            await add_money(gid, uid, amt, "explore")
            await interaction.followup.send(embed=embed("Found cash", f"+{fmt_money(amt)}"))
            return
        if kind == "item":
            from database.repositories.inventory import add_item
            await add_item(gid, uid, "milk", 1)
            await interaction.followup.send(embed=embed("Convenience store", "Found Choco Milk x1 (`/inventory`)"))
            return
        if kind == "trainer":
            await interaction.followup.send(embed=embed("A coach watches",
                "A trainer is nearby. Use `/trainers` to see who can train you."))
            return
        if kind == "boss":
            await interaction.followup.send(embed=embed("Heavy aura",
                "A boss-level presence... check `/bosses` when you're stronger. A street fighter blocks you instead."))
            kind = "fighter"

        # fighter / named: pick a recruitable def of rolled rarity near level
        rarity = enc.get("rarity", "Common")
        async with SessionLocal() as s:
            r = await s.execute(select(CharacterDefinition).where(
                CharacterDefinition.recruitable == 1, CharacterDefinition.rarity == rarity))
            pool = r.scalars().all()
            if not pool:
                r = await s.execute(select(CharacterDefinition).where(CharacterDefinition.recruitable == 1))
                pool = r.scalars().all()
            d = random.choice(pool)
            s.expunge(d)

        pw = power_score(d.base_str, d.base_spd, d.base_end, d.base_tech, d.base_iq)
        e = embed(f"Encounter: {d.name} [{d.rarity}]",
                  f"{d.style} • {d.faction} • POW ~{pw}\n{d.description}\n\nFight to recruit. Win = high chance.")
        # card image (cached, offloaded)
        img_path = None
        try:
            from utils import image_utils
            loop = asyncio.get_running_loop()
            img_path = await loop.run_in_executor(
                None, image_utils.character_card, d.name, d.rarity, d.style, d.faction, pw,
                {"STR": d.base_str, "SPD": d.base_spd, "END": d.base_end, "TEC": d.base_tech, "IQ": d.base_iq})
            e.set_image(url="attachment://card.png")
        except Exception:
            img_path = None

        state = {"def_id": d.id, "rarity": d.rarity, "min_level": d.min_level}

        async def do_fight(itr: discord.Interaction):
            await itr.response.defer()
            pl = await repo.get_or_create_player(gid, uid, itr.user.display_name)
            async with SessionLocal() as s2:
                dd = await s2.get(CharacterDefinition, state["def_id"])
                s2.expunge(dd)
            scale = 0.85 + min(0.5, pl.level * 0.02)
            res = combat_service.simulate(_player_combatant(pl), _def_combatant(dd, scale), seed=random.randint(1, 999999))
            won = res["winner_side"] == "A"
            b = await create_battle(gid, "pve", uid)
            await resolve_battle(b.id, uid if won else 0, {"log": res["log"]})
            ch = recruit_chance(state["rarity"], won, pl.level, state["min_level"], pl.reputation)
            lines = "\n".join(res["log"][-8:])
            if won:
                xp = res["xp"]
                async with SessionLocal() as s3:
                    from database.models import Player as PM
                    r3 = await s3.execute(select(PM).where(PM.guild_id == gid, PM.user_id == uid))
                    row = r3.scalar_one()
                    row.xp += xp
                    row.wins += 1
                    # level ups
                    from utils.formatting import xp_for_level as need
                    while row.xp >= need(row.level):
                        row.xp -= need(row.level)
                        row.level += 1
                        row.p_str += 2; row.p_spd += 2; row.p_end += 2; row.p_tech += 2
                    await s3.commit()
                await add_money(gid, uid, 120, "fight_win", ref=f"battle:{b.id}")
                await itr.followup.send(
                    embed=embed(f"Won vs {dd.name} (+{xp} XP, +120 Won)",
                                f"{lines}\n\nRecruit chance {int(ch*100)}% — press Recruit to try."))
                # store winnable recruit in short cooldown row
                await repo.set_cooldown(gid, uid, f"recruit:{dd.id}", 300)
            else:
                async with SessionLocal() as s3:
                    from database.models import Player as PM
                    r3 = await s3.execute(select(PM).where(PM.guild_id == gid, PM.user_id == uid))
                    row = r3.scalar_one()
                    row.losses += 1
                    await s3.commit()
                await itr.followup.send(embed=embed(f"Lost vs {dd.name}", lines, color=0xED4245))

        async def do_recruit(itr: discord.Interaction):
            await itr.response.defer(ephemeral=True)
            # must have fought recently (cooldown marker) to prevent free claims
            cd = await repo.get_cooldown(gid, uid, f"recruit:{state['def_id']}")
            from utils.cooldowns import on_cooldown
            pl = await repo.get_or_create_player(gid, uid, itr.user.display_name)
            ch = recruit_chance(state["rarity"], bool(cd and on_cooldown(cd.expires_at)),
                                pl.level, state["min_level"], pl.reputation)
            if random.random() < ch:
                # roster cap: 20 + level
                from database.repositories.characters import count_instances
                n = await count_instances(gid, uid)
                if n >= 20 + pl.level:
                    await itr.followup.send("Roster full. Release someone first.")
                    return
                inst = await add_instance(gid, uid, state["def_id"])
                await itr.followup.send(f"**{state['def_id']} joined your crew!** (#{inst.id}) Use `/team` to field them.")
            else:
                await itr.followup.send("They refused. Win a fight first, then try again.")

        async def do_run(itr: discord.Interaction):
            await itr.response.send_message("You slipped away.", ephemeral=True)

        view = EncounterView(uid, do_fight, do_recruit, do_run)
        if img_path:
            await interaction.followup.send(embed=e, file=discord.File(img_path, filename="card.png"), view=view)
        else:
            await interaction.followup.send(embed=e, view=view)


async def setup(bot):
    await bot.add_cog(Exploration(bot))
