import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import ItemDefinition
from database.repositories import players as repo
from database.repositories.economy import add_money
from database.repositories.inventory import add_item, list_inventory, remove_item
from utils.embeds import embed, error_embed
from utils.formatting import fmt_money
from utils.permissions import clamp_amount
from views.pagination import PagedEmbed, chunk


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Browse the CU + HNH shop")
    async def shop(self, interaction: discord.Interaction):
        async with SessionLocal() as s:
            r = await s.execute(select(ItemDefinition))
            items = r.scalars().all()
        pages = []
        for part in chunk(items, 6):
            pages.append(embed("Shop", "\n".join(f"`{i.id}` {i.name} [{i.rarity}] — {fmt_money(i.price)}\n_{i.description}_" for i in part)))
        await interaction.response.send_message(embed=pages[0],
            view=PagedEmbed(pages, interaction.user.id) if len(pages) > 1 else None, ephemeral=True)

    @app_commands.command(name="buy", description="Buy an item")
    @app_commands.describe(item_id="Item id", qty="Quantity")
    async def buy(self, interaction: discord.Interaction, item_id: str, qty: int = 1):
        qty = clamp_amount(qty, 1, 99)
        await interaction.response.defer(ephemeral=True)
        async with SessionLocal() as s:
            d = await s.get(ItemDefinition, item_id)
            if not d:
                await interaction.followup.send(embed=error_embed("Unknown item."))
                return
            cost = d.price * qty
        try:
            await add_money(interaction.guild_id, interaction.user.id, -cost, "shop_buy", ref=item_id)
        except ValueError:
            await interaction.followup.send(embed=error_embed("Not enough Won."))
            return
        await add_item(interaction.guild_id, interaction.user.id, item_id, qty)
        await interaction.followup.send(f"Bought {d.name} x{qty} for {fmt_money(cost)}.")

    @app_commands.command(name="sell", description="Sell an item back (70%)")
    async def sell(self, interaction: discord.Interaction, item_id: str, qty: int = 1):
        qty = clamp_amount(qty, 1, 99)
        await interaction.response.defer(ephemeral=True)
        async with SessionLocal() as s:
            d = await s.get(ItemDefinition, item_id)
            if not d:
                await interaction.followup.send(embed=error_embed("Unknown item."))
                return
        try:
            await remove_item(interaction.guild_id, interaction.user.id, item_id, qty)
        except ValueError:
            await interaction.followup.send(embed=error_embed("You don't have that many."))
            return
        gain = int(d.price * 0.7) * qty
        await add_money(interaction.guild_id, interaction.user.id, gain, "shop_sell", ref=item_id)
        await interaction.followup.send(f"Sold {d.name} x{qty} for +{fmt_money(gain)}.")

    @app_commands.command(name="inventory", description="Show your inventory")
    async def inventory(self, interaction: discord.Interaction):
        rows = await list_inventory(interaction.guild_id, interaction.user.id)
        if not rows:
            await interaction.response.send_message("Empty.", ephemeral=True)
            return
        async with SessionLocal() as s:
            lines = []
            for r in rows:
                d = await s.get(ItemDefinition, r.item_id)
                lines.append(f"{d.name} x{r.qty}" + (f" (on #{r.equipped_to})" if r.equipped_to else ""))
        await interaction.response.send_message(embed=embed("Inventory", "\n".join(lines)), ephemeral=True)

    @app_commands.command(name="use", description="Use a consumable (milk = energy)")
    async def use(self, interaction: discord.Interaction, item_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await remove_item(interaction.guild_id, interaction.user.id, item_id, 1)
        except ValueError:
            await interaction.followup.send(embed=error_embed("None left."))
            return
        async with SessionLocal() as s:
            d = await s.get(ItemDefinition, item_id)
            fx = dict(d.effects or {})
        if "energy" in fx:
            p = await repo.get_or_create_player(interaction.guild_id, interaction.user.id, interaction.user.display_name)
            p.energy = min(100, p.energy + int(fx["energy"]))
            await repo.save_player(p)
            await interaction.followup.send(f"Used {d.name}: +{fx['energy']} energy.")
        else:
            # refund non-consumables to avoid accidental loss
            await add_item(interaction.guild_id, interaction.user.id, item_id, 1)
            await interaction.followup.send("That isn't usable with /use. Weapons equip via `/equip`.")


    # ---- prefix mirrors ----

    @commands.command(name="shop", aliases=["store"])
    async def shop_prefix(self, ctx: commands.Context):
        async with SessionLocal() as s:
            r = await s.execute(select(ItemDefinition))
            items = r.scalars().all()
        txt = "\n".join(f"`{i.id}` {i.name} [{i.rarity}] — {fmt_money(i.price)}" for i in items)
        await ctx.send(embed=embed("Shop", txt))

    @commands.command(name="buy")
    async def buy_prefix(self, ctx: commands.Context, item_id: str, qty: int = 1):
        qty = clamp_amount(qty, 1, 99)
        async with SessionLocal() as s:
            d = await s.get(ItemDefinition, item_id)
            if not d:
                await ctx.send(embed=error_embed("Unknown item."))
                return
            cost = d.price * qty
        try:
            await add_money(ctx.guild.id, ctx.author.id, -cost, "shop_buy", ref=item_id)
        except ValueError:
            await ctx.send(embed=error_embed("Not enough Won."))
            return
        await add_item(ctx.guild.id, ctx.author.id, item_id, qty)
        await ctx.send(f"Bought {d.name} x{qty} for {fmt_money(cost)}.")

    @commands.command(name="sell")
    async def sell_prefix(self, ctx: commands.Context, item_id: str, qty: int = 1):
        qty = clamp_amount(qty, 1, 99)
        async with SessionLocal() as s:
            d = await s.get(ItemDefinition, item_id)
            if not d:
                await ctx.send(embed=error_embed("Unknown item."))
                return
        try:
            await remove_item(ctx.guild.id, ctx.author.id, item_id, qty)
        except ValueError:
            await ctx.send(embed=error_embed("You don't have that many."))
            return
        gain = int(d.price * 0.7) * qty
        await add_money(ctx.guild.id, ctx.author.id, gain, "shop_sell", ref=item_id)
        await ctx.send(f"Sold {d.name} x{qty} for +{fmt_money(gain)}.")

    @commands.command(name="inventory", aliases=["inv", "bag"])
    async def inventory_prefix(self, ctx: commands.Context):
        rows = await list_inventory(ctx.guild.id, ctx.author.id)
        if not rows:
            await ctx.send("Empty.")
            return
        async with SessionLocal() as s:
            lines = []
            for r in rows:
                d = await s.get(ItemDefinition, r.item_id)
                lines.append(f"{d.name} x{r.qty}" + (f" (on #{r.equipped_to})" if r.equipped_to else ""))
        await ctx.send(embed=embed("Inventory", "\n".join(lines)))

    @commands.command(name="use")
    async def use_prefix(self, ctx: commands.Context, item_id: str):
        try:
            await remove_item(ctx.guild.id, ctx.author.id, item_id, 1)
        except ValueError:
            await ctx.send(embed=error_embed("None left."))
            return
        async with SessionLocal() as s:
            d = await s.get(ItemDefinition, item_id)
            fx = dict(d.effects or {})
        if "energy" in fx:
            p = await repo.get_or_create_player(ctx.guild.id, ctx.author.id, ctx.author.display_name)
            p.energy = min(100, p.energy + int(fx["energy"]))
            await repo.save_player(p)
            await ctx.send(f"Used {d.name}: +{fx['energy']} energy.")
        else:
            await add_item(ctx.guild.id, ctx.author.id, item_id, 1)
            await ctx.send("That isn't usable with `c!use`.")


async def setup(bot):
    await bot.add_cog(Economy(bot))
