import discord
from discord import ui


class PagedEmbed(ui.View):
    def __init__(self, pages: list[discord.Embed], author_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.idx = 0
        self.author_id = author_id
        self._sync()

    def _sync(self):
        self.prev_btn.disabled = self.idx <= 0
        self.next_btn.disabled = self.idx >= len(self.pages) - 1

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("These buttons aren't yours.", ephemeral=True)
            return False
        return True

    @ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check(interaction):
            return
        self.idx = max(0, self.idx - 1)
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.idx], view=self)

    @ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check(interaction):
            return
        self.idx = min(len(self.pages) - 1, self.idx + 1)
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.idx], view=self)


def chunk(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
