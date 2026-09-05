import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import embed

SECTIONS = {
    "Getting Started": "/profile → /explore → Fight → Recruit → /team → /train → /shop",
    "Combat": "/explore, /fight @user, /boss, styles matter, fatigue matters",
    "Characters": "/collection, /team ids:1,2, /dex <name>",
    "Training": "/trainers, /train <id> <trainer>, /claim_train, /mastery, /bloodline",
    "Crews": "/crew create/join/info/leave/war",
    "Territories": "/territories, /conquer <name>",
    "Economy": "/balance, /daily, /shop, /buy, /sell, /inventory, /use",
    "PvP": "/fight @user wager:100 — ranked pot, bounty up",
    "Quests": "/quests, /claim_quest <id>, /events, /generations, /workers",
    "Bosses": "/bosses, /boss <name> — phases + cooldowns",
}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Crewism guide")
    @app_commands.describe(section="Which section")
    async def help(self, interaction: discord.Interaction, section: str = "Getting Started"):
        txt = SECTIONS.get(section, "\n".join(f"**{k}**: {v}" for k, v in SECTIONS.items()))
        await interaction.response.send_message(embed=embed(f"Help — {section}", txt), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
