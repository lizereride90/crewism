import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import embed

SECTIONS = {
    "Getting Started": "`/profile` or `c!profile` → `c!explore` → Fight → Recruit → `c!team` → `c!train` → `c!shop`",
    "Combat": "`/explore`, `/fight @user`, `/boss` — or prefix: `c!explore`, `c!fight @user`, `c!boss`. Styles matter, fatigue matters.",
    "Characters": "`c!collection`, `c!team 1,2`, `c!dex <name>`",
    "Training": "`c!trainers`, `c!train <id> <trainer>`, `c!claim_train`, `c!mastery`, `c!bloodline`",
    "Crews": "`c!crew_create <name>`, `c!crew_join <name>`, `c!crew_info`, `c!crew_leave`, `c!crew_war <enemy>`",
    "Territories": "`c!territories`, `c!conquer <name>`",
    "Economy": "`c!balance`, `c!daily`, `c!shop`, `c!buy <id>`, `c!sell <id>`, `c!inventory`, `c!use <id>`",
    "Gambling": "`c!coinflip heads 100`, `c!dice 100`, `c!higherlower 100` (fictional Won)",
    "PvP": "`c!fight @user 100` — ranked pot, bounty up",
    "Quests": "`c!quests`, `c!claim_quest <id>`, `c!events`, `c!generations`, `c!workers`",
    "Bosses": "`/boss` or `c!boss` — dropdown/pick list, phases + cooldowns",
}

PREFIX_LIST = """**Every slash command has a `c!` twin:**
`c!profile c!balance c!daily c!stats c!explore c!collection c!team c!dex`
`c!boss c!trainers c!train c!claim_train c!mastery c!bloodline`
`c!shop c!buy c!sell c!inventory c!use c!coinflip c!dice c!higherlower`
`c!fight @user c!crew_create c!crew_join c!crew_info c!crew_leave c!crew_war`
`c!territories c!conquer c!quests c!claim_quest c!events c!generations c!workers`
`c!leaderboard c!bounty c!help`"""


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Crewism guide")
    @app_commands.describe(section="Which section")
    async def help(self, interaction: discord.Interaction, section: str = "Getting Started"):
        txt = SECTIONS.get(section, "\n".join(f"**{k}**: {v}" for k, v in SECTIONS.items()))
        await interaction.response.send_message(embed=embed(f"Help — {section}", txt), ephemeral=True)

    @commands.command(name="help", aliases=["h", "commands"])
    async def help_prefix(self, ctx: commands.Context, *, section: str = ""):
        if section and section in SECTIONS:
            await ctx.send(embed=embed(f"Help — {section}", SECTIONS[section]))
        else:
            await ctx.send(embed=embed("Crewism help — slash or c! prefix", PREFIX_LIST))


async def setup(bot):
    bot.remove_command("help")  # drop built-in so c!help is ours
    await bot.add_cog(Help(bot))
