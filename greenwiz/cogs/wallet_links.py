from discord.ext import commands
from typing import Any

from wax_chain.wax_addresses import is_valid_wax_address
from utils.meta_cog import MetaCog
from utils.settings import WALLETLINK_LOG_CHANNEL


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
        """Set your wallet to make the Green Wizard send any future drops directly there!
        For example, if your address is `cmcdrops4all`, use `,setwallet cmcdrops4all`.
        If you change your mind, you can always choose to clear this by using `,clearwallet`.
        """
        log_channel = self.bot.get_channel(WALLETLINK_LOG_CHANNEL)
        if not is_valid_wax_address(wallet, valid_specials=self.bot.special_addr_list, case_sensitive=True):
            await ctx.send(f"Invalid wallet {wallet}")
            return
        await log_channel.send(f"User <@{ctx.author.id}> set their wallet to {wallet}")

        await self.bot.storage[None].set_note(ctx.author, "LinkedWallet", wallet)
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
            log_channel = self.bot.get_channel(WALLETLINK_LOG_CHANNEL)
            await log_channel.send(f"User <@{ctx.author.id}> cleared their set wallet")
            await ctx.send("Linked wallet cleared")


async def setup(bot):
    await bot.add_cog(WalletLinks(bot))
