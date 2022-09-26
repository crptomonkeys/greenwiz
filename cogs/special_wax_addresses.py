from discord.ext import tasks

from utils.meta_cog import MetaCog
from utils.wax_addresses import async_get_special_wax_address_list


class SpecialWaxAddresses(MetaCog):
    """A small cog which takes care of maintaining a list of valid special wax addresses for the bot."""

    def __init__(self, bot):
        super().__init__(bot)
        self.bot.special_addr_list = set()
        self.update_valid_special_wax_list.start()
        self.bot.log(
            "Started the update_valid_special_wax_list task (1).", self.bot.debug
        )

    def cog_unload(self):
        self.update_valid_special_wax_list.cancel()
        self.bot.log("Ended the update_valid_special_wax_list task.", self.bot.debug)

    @tasks.loop(seconds=28800)
    async def update_valid_special_wax_list(self):
        specials = await async_get_special_wax_address_list(self.bot.session)
        self.bot.special_addr_list.update(specials)
        self.bot.log(
            f"Updated cached list of {len(self.bot.special_addr_list)} special wax addresses."
        )

    @update_valid_special_wax_list.before_loop
    async def before_update_valid_special_wax_list(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SpecialWaxAddresses(bot))
