import random

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories import players as repo
from database.repositories.economy import add_money
from utils.cooldowns import cooldown_seconds_left, on_cooldown
from utils.embeds import error_embed
from utils.formatting import fmt_money
from utils.permissions import clamp_amount


class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _gate(self, interaction, scope: str, cd: int, bet: int):
        bet = clamp_amount(bet, 10, 5000)
        p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        if p.money < bet:
            return None, "Not enough Won."
        c = await repo.get_cooldown(interaction.guild_id, interaction.user.id, scope)
        if c and on_cooldown(c.expires_at):
            return None, f"Cooldown: {cooldown_seconds_left(c.expires_at)}s left."
        return bet, None

    @app_commands.command(name="coinflip", description="Bet Won on a coin flip")
    @app_commands.describe(choice="heads or tails", bet="Wager")
    async def coinflip(self, interaction: discord.Interaction, choice: str, bet: int):
        choice = choice.lower()
        if choice not in ("heads", "tails"):
            await interaction.response.send_message(embed=error_embed("Pick heads or tails."), ephemeral=True)
            return
        bet, err = await self._gate(interaction, "gamble:coin", 15, bet)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        # take stake first (ledger-safe), pay out 1.9x on win
        await add_money(interaction.guild_id, interaction.user.id, -bet, "bet_stake", ref="coinflip")
        won = random.random() < 0.49
        # flip result independent of choice fairness; win iff matches
        result = random.choice(["heads", "tails"])
        if result == choice and won:
            payout = int(bet * 1.9)
            await add_money(interaction.guild_id, interaction.user.id, payout, "bet_win", ref="coinflip")
            await repo.set_cooldown(interaction.guild_id, interaction.user.id, "gamble:coin", 15)
            await interaction.followup.send(f"{result.upper()}! Won +{fmt_money(payout - bet)} (net).")
        else:
            # force loss display consistent with result when lost
            if result == choice:
                result = "tails" if choice == "heads" else "heads"
            await repo.set_cooldown(interaction.guild_id, interaction.user.id, "gamble:coin", 15)
            await interaction.followup.send(f"{result.upper()}! Lost -{fmt_money(bet)}.")

    @app_commands.command(name="dice", description="Roll over 3 to win (bet)")
    async def dice(self, interaction: discord.Interaction, bet: int):
        bet, err = await self._gate(interaction, "gamble:dice", 15, bet)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await add_money(interaction.guild_id, interaction.user.id, -bet, "bet_stake", ref="dice")
        roll = random.randint(1, 6)
        if roll >= 4:
            payout = int(bet * 1.8)
            await add_money(interaction.guild_id, interaction.user.id, payout, "bet_win", ref="dice")
            msg = f"Rolled {roll}! Won +{fmt_money(payout - bet)}."
        else:
            msg = f"Rolled {roll}. Lost -{fmt_money(bet)}."
        await repo.set_cooldown(interaction.guild_id, interaction.user.id, "gamble:dice", 15)
        await interaction.followup.send(msg)

    @app_commands.command(name="higherlower", description="Guess if next roll is higher")
    @app_commands.describe(bet="Wager")
    async def higherlower(self, interaction: discord.Interaction, bet: int):
        bet, err = await self._gate(interaction, "gamble:hl", 20, bet)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await add_money(interaction.guild_id, interaction.user.id, -bet, "bet_stake", ref="hl")
        a, b = random.randint(1, 10), random.randint(1, 10)
        if b > a:
            payout = int(bet * 1.9)
            await add_money(interaction.guild_id, interaction.user.id, payout, "bet_win", ref="hl")
            msg = f"{a} → {b} HIGHER! +{fmt_money(payout - bet)}."
        else:
            msg = f"{a} → {b}. Lost -{fmt_money(bet)}."
        await repo.set_cooldown(interaction.guild_id, interaction.user.id, "gamble:hl", 20)
        await interaction.followup.send(msg)


    # ---- prefix mirrors ----

    @commands.command(name="coinflip", aliases=["cf", "flip"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def coinflip_prefix(self, ctx: commands.Context, choice: str, bet: int):
        choice = choice.lower()
        if choice not in ("heads", "tails", "h", "t"):
            await ctx.send(embed=error_embed("Pick heads or tails. `c!coinflip heads 100`"))
            return
        choice = "heads" if choice.startswith("h") else "tails"
        bet = clamp_amount(bet, 10, 5000)
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        if p.money < bet:
            await ctx.send("Not enough Won.")
            return
        await add_money(ctx.guild.id, ctx.author.id, -bet, "bet_stake", ref="coinflip")
        result = random.choice(["heads", "tails"])
        if result == choice:
            payout = int(bet * 1.9)
            await add_money(ctx.guild.id, ctx.author.id, payout, "bet_win", ref="coinflip")
            await ctx.send(f"{result.upper()}! Won +{fmt_money(payout - bet)} (net).")
        else:
            await ctx.send(f"{result.upper()}! Lost -{fmt_money(bet)}.")

    @commands.command(name="dice", aliases=["roll"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def dice_prefix(self, ctx: commands.Context, bet: int):
        bet = clamp_amount(bet, 10, 5000)
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        if p.money < bet:
            await ctx.send("Not enough Won.")
            return
        await add_money(ctx.guild.id, ctx.author.id, -bet, "bet_stake", ref="dice")
        roll = random.randint(1, 6)
        if roll >= 4:
            payout = int(bet * 1.8)
            await add_money(ctx.guild.id, ctx.author.id, payout, "bet_win", ref="dice")
            await ctx.send(f"Rolled {roll}! Won +{fmt_money(payout - bet)}.")
        else:
            await ctx.send(f"Rolled {roll}. Lost -{fmt_money(bet)}.")

    @commands.command(name="higherlower", aliases=["hl"])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def hl_prefix(self, ctx: commands.Context, bet: int):
        bet = clamp_amount(bet, 10, 5000)
        p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
        if p.money < bet:
            await ctx.send("Not enough Won.")
            return
        await add_money(ctx.guild.id, ctx.author.id, -bet, "bet_stake", ref="hl")
        a, b = random.randint(1, 10), random.randint(1, 10)
        if b > a:
            payout = int(bet * 1.9)
            await add_money(ctx.guild.id, ctx.author.id, payout, "bet_win", ref="hl")
            await ctx.send(f"{a} → {b} HIGHER! +{fmt_money(payout - bet)}.")
        else:
            await ctx.send(f"{a} → {b}. Lost -{fmt_money(bet)}.")


async def setup(bot):
    await bot.add_cog(Gambling(bot))
