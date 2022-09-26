import discord
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.settings import CM_GUID


class LinkDeleter(MetaCog):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only for posts in the intro channel
        if not message.guild:
            return
        if message.guild.id != CM_GUID:
            return
        role = message.guild.get_role(822929698358820905)
        author = message.guild.get_member(message.author.id)
        if author is None or role not in author.roles:
            return

        if (
            "http://" in message.content
            or "https://" in message.content
            or "www." in message.content
        ):
            await message.delete()
            await message.channel.send(
                f"{message.author.mention}, you're not allowed to post links in chat!"
            )


async def setup(bot):
    await bot.add_cog(LinkDeleter(bot))
