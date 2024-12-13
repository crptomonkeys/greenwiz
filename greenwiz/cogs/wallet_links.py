from discord.ext import commands
from typing import Any

from wax_chain.wax_addresses import is_valid_wax_address
from utils.meta_cog import MetaCog


class WalletLinks(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.hybrid_command(
        description="Set wallet to which future drops will be sent directly to.",
        aliases=["setwallet", "linkwallet"]
    )
    async def set_wallet(
        self, ctx: commands.Context[Any], wallet: str
    ):
        if not is_valid_wax_address(wallet, valid_specials=self.bot.special_addr_list, case_sensitive=True):
            await ctx.send(f"Invalid wallet {wallet}")
            return
        try:
            await self.bot.storage[None].set_note(ctx.author, "LinkedWallet", wallet)
        except Exception as e:
            await ctx.send(f"Failed to set wallet {e}")
            return
        await ctx.send("Successfully set wallet")

    @commands.hybrid_command(
        description="Get your currently set wallet.",
        aliases=["getwallet"]
    )
    async def get_wallet(
        self, ctx: commands.Context[Any]
    ):
        wallet = await self.bot.storage[None].get_note(ctx.author, "LinkedWallet")
        if wallet == "Not found.":
            await ctx.send("No wallet currenty linked.")
        else:
            await ctx.send(f"Current linked wallet: {wallet}")

    @commands.hybrid_command(
        description="Clear your currently set wallet to receive claimlinks again.",
        aliases=["clearwallet"]
    )
    async def clear_wallet(
        self, ctx: commands.Context[Any]
    ):
        wallet = await self.bot.storage[None].get_note(ctx.author, "LinkedWallet")
        if wallet == "Not found.":
            await ctx.send("No wallet currenty linked.")
        else:
            await self.bot.storage[None].del_note(ctx.author, "LinkedWallet")
            await ctx.send("Linked wallet cleared")


async def setup(bot):
    await bot.add_cog(WalletLinks(bot))
