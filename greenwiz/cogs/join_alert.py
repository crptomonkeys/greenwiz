import discord
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.settings import CM_GUID, DEFAULT_FALLBACK_CHANNEL


class JoinAlert(MetaCog):
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Only for cryptomonKeys server atm
        if member.guild.id != CM_GUID:
            return

        embed = discord.Embed(title=f"{member} joined", color=member.color)
        embed.set_author(
            icon_url=member.display_avatar.url, name=f"{member.name} ({member.id})"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        created = int(member.created_at.timestamp())
        if member.joined_at is None:
            joined = created
        else:
            joined = int(member.joined_at.timestamp())
        embed.add_field(name="Created:", value=f"<t:{created}:R>\n<t:{created}:f>")
        embed.add_field(name="Joined:", value=f"<t:{joined}:R>\n<t:{joined}:f>")

        welcome_channel = self.bot.get_channel(763477318861455411)
        try:
            await welcome_channel.send(f"{member.mention}", embed=embed)
        except discord.Forbidden:
            ch = self.bot.get_channel(DEFAULT_FALLBACK_CHANNEL)
            await ch.send(f"{member.mention}", embed=embed)


async def setup(bot):
    await bot.add_cog(JoinAlert(bot))
