import asyncio
import discord
from discord import Forbidden
from discord.ext import commands

from utils.meta_cog import MetaCog


class IntroSilencer(MetaCog):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only for posts in the intro channel
        if not message.guild:
            return
        if message.channel.id != 758054443479597077:
            return

        role: commands.Snowflake = commands.Snowflake(
            message.guild.get_role(816406154778378322)
        )
        if not isinstance(message.author, discord.Member):
            raise AssertionError(
                "Guild messages' author attribute should always be a Member."
            )
        while role not in message.author.roles:
            # To ensure role gets added even if it was missed initially.
            try:
                await message.author.add_roles(role)
            except Forbidden:
                # No perms to add role
                self.log(
                    f"No permissions to add user roles in guild {message.guild} ({message.guild.id})",
                    "WARN",
                )
                break
            await asyncio.sleep(1)


async def setup(bot):
    await bot.add_cog(IntroSilencer(bot))
