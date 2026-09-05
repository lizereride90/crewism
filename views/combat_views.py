import asyncio

import discord
from discord import ui


class EncounterView(ui.View):
    """Buttons call back into cog methods via callbacks dict. Expires safely."""

    def __init__(self, author_id: int, on_fight, on_recruit, on_run, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self._fight = on_fight
        self._recruit = on_recruit
        self._run = on_run
        self.resolved = False

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This encounter isn't yours.", ephemeral=True)
            return False
        if self.resolved:
            await interaction.response.send_message("Already resolved.", ephemeral=True)
            return False
        return True

    @ui.button(label="Fight", style=discord.ButtonStyle.danger)
    async def fight(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check(interaction):
            return
        self.resolved = True
        await self._fight(interaction)
        self.stop()

    @ui.button(label="Recruit", style=discord.ButtonStyle.success)
    async def recruit(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check(interaction):
            return
        self.resolved = True
        await self._recruit(interaction)
        self.stop()

    @ui.button(label="Run", style=discord.ButtonStyle.secondary)
    async def run(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check(interaction):
            return
        self.resolved = True
        await self._run(interaction)
        self.stop()


async def send_card(interaction: discord.Interaction, embed: discord.Embed, image_path: str | None):
    if image_path:
        loop = asyncio.get_running_loop()
        # file send is quick; no heavy work here (generation already cached/offloaded)
        file = discord.File(image_path, filename="card.png")
        embed.set_image(url="attachment://card.png")
        await interaction.followup.send(embed=embed, file=file)
    else:
        await interaction.followup.send(embed=embed)
