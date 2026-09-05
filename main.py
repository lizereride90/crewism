import asyncio
import logging
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks

import dashboard_api
from config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                    format="%(asctime)s %(name)s %(levelname)s: %(message)s")
log = logging.getLogger("crewism")

COGS = [
    "cogs.profile", "cogs.exploration", "cogs.characters", "cogs.combat",
    "cogs.training", "cogs.economy", "cogs.gambling", "cogs.pvp",
    "cogs.crews", "cogs.territories", "cogs.quests", "cogs.leaderboard", "cogs.help",
]


class CrewismBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # required for c! prefix commands
        super().__init__(command_prefix="c!", intents=intents)


bot = CrewismBot()


@tasks.loop(hours=1)
async def hourly_upkeep():
    """Territory income + event expiry. DB-backed so restarts are safe."""
    try:
        from datetime import datetime

        from sqlalchemy import select

        from database.connection import SessionLocal
        from database.models import Crew, Event, Territory, TerritoryOwnership
        from database.repositories.economy import add_money

        async with SessionLocal() as s:
            rows = (await s.execute(select(TerritoryOwnership).where(TerritoryOwnership.owner_type == "crew"))).scalars().all()
            terrs = {t.id: t for t in (await s.execute(select(Territory))).scalars().all()}
            for o in rows:
                t = terrs.get(o.territory_id)
                if not t or not o.crew_id:
                    continue
                hourly = max(1, t.income // 24)
                # credit crew treasury
                c = await s.get(Crew, o.crew_id)
                if c:
                    c.treasury += hourly
            # expire events
            evs = (await s.execute(select(Event).where(Event.active == 1))).scalars().all()
            for e in evs:
                if e.ends_at and e.ends_at < datetime.utcnow():
                    e.active = 0
            await s.commit()
    except Exception as e:
        log.warning("upkeep failed: %s", e)


@bot.event
async def on_ready():
    log.info("logged in as %s in %d guilds", bot.user, len(bot.guilds))
    dashboard_api.attach_bot(bot, datetime.utcnow())
    try:
        if settings.command_guild_id:
            guild = discord.Object(id=settings.command_guild_id)
            await bot.tree.sync(guild=guild)
            # delete stale global duplicates so commands don't show twice
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
        else:
            await bot.tree.sync()
        log.info("slash commands synced")
    except Exception as e:
        log.error("sync failed: %s", e)


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Cooldown. Try again in {int(error.retry_after)}s.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Bad arguments. Try `c!help`.")
    else:
        await ctx.send("Something broke. Try again.")
    log.warning("prefix error: %r", error)


@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error):
    try:
        msg = "Something broke. Try again."
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            msg = f"Cooldown. Try again in {int(error.retry_after)}s."
        elif isinstance(error, discord.app_commands.MissingPermissions):
            msg = "Missing permissions."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass
    log.warning("command error: %r", error)


async def start_dashboard():
    """Launch the Node dashboard UI as a child process (after the bot is up).

    Single entrypoint: `python main.py` boots bot first, then dash.
    Shares DASHBOARD_TOKEN with the local bot API; generates a session
    token when none is configured. Never fatal — bot runs without UI.
    """
    import shutil

    if not shutil.which("node"):
        log.warning("node not found — dashboard UI disabled (bot still runs)")
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", "dashboard/server.js",
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=os.environ,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        log.info("dashboard UI → http://localhost:%s", os.environ["DASH_PORT"])
        return proc
    except Exception as e:  # noqa: BLE001 - UI must never kill the bot
        log.warning("dashboard failed to start: %s", e)
        return None


async def main():
    import secrets

    # shared secret for bot API <-> dashboard UI (generated per run if unset)
    if not os.getenv("DASHBOARD_TOKEN"):
        os.environ["DASHBOARD_TOKEN"] = secrets.token_hex(24)
        log.info("generated session DASHBOARD_TOKEN")
    os.environ.setdefault("DASHBOARD_PORT", "3100")
    os.environ.setdefault("DASH_PORT", "3000")
    os.makedirs(settings.image_cache_dir, exist_ok=True)
    os.makedirs("assets/generated", exist_ok=True)
    from database.connection import init_db

    await init_db()
    from services.seed_service import seed_all

    await seed_all()
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info("loaded %s", cog)
        except Exception as e:
            log.error("failed loading %s: %s", cog, e)
    hourly_upkeep.start()
    dashboard_api.start(port=int(os.getenv("DASHBOARD_PORT", "3100")))
    if not settings.token:
        raise SystemExit("Missing DISCORD_TOKEN in .env (see .env.example)")
    dash_proc = await start_dashboard()
    try:
        async with bot:
            await bot.start(settings.token)
    finally:
        if dash_proc and dash_proc.returncode is None:
            try:
                dash_proc.terminate()
            except ProcessLookupError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
