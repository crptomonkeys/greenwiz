import itertools
from datetime import datetime, timezone, timedelta

import discord
import psutil
import pygit2
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.util import utcnow
from utils.exceptions import UnableToCompleteRequestedAction

GIT_URL = "https://github.com/crptomonkeys/greenwiz"


def format_commit(commit):
    short, _, _ = commit.message.partition("\n")
    commit_tz = timezone(timedelta(minutes=commit.commit_time_offset))
    commit_time = datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)
    stamp = int(commit_time.timestamp() - 0.6)
    return f"<t:{stamp}:R> : {short}"


class About(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.process = psutil.Process()
        # If this isn't run near startup, the first time about is invoked cpu perc will display as zero
        self.process.cpu_percent()

    # ==================== Commands ====================

    @commands.hybrid_command()
    async def invite(self, ctx):
        """Send an invite link for the bot in chat."""
        await ctx.send(
            f"Invite me to your server:\n"
            f"{discord.utils.oauth_url(ctx.me.id, permissions=discord.Permissions(permissions=8))}"
        )

    @commands.hybrid_command()
    async def about(self, ctx):
        """Tells you information about the bot itself."""
        _name = "Built by Vyryn for cryptomonKeys.cc"
        if self.bot.settings.ENV != "prod":
            _name += f" (Running in {self.bot.settings.ENV})"
        try:
            repo = pygit2.Repository(".git")
        except pygit2.GitError:
            try:
                repo = pygit2.Repository("../.git")
            except pygit2.GitError:
                raise UnableToCompleteRequestedAction(
                    "Sorry, my git repo isn't configured correctly for the about command at the moment."
                )
        commits = list(
            itertools.islice(
                repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), 5
            )
        )
        revision = "\n".join(format_commit(c) for c in commits)
        last_update = format_commit(commits[0]).split(" ")[0]
        embed = discord.Embed(
            description="**Latest Changes**:\n" + revision, timestamp=utcnow()
        )
        embed.title = "Invite Me To Your Server"
        embed.url = discord.utils.oauth_url(
            ctx.me.id, permissions=discord.Permissions(permissions=8)
        )
        embed.colour = discord.Colour.darker_grey()

        owner = await self.bot.fetch_user(self.bot.owner_id)
        embed.set_author(
            name=_name,
            icon_url=owner.display_avatar.url,
            url=GIT_URL,
        )

        unique_members = len(self.bot.users)
        members, tc, vc, total_c, guilds = 0, 0, 0, 0, 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.member_count:
                members += guild.member_count
            total_c += len(guild.channels)
            for channel in guild.channels:
                if channel.type in [
                    discord.ChannelType.text,
                    discord.ChannelType.news,
                    discord.ChannelType.forum,
                    discord.ChannelType.news_thread,
                    discord.ChannelType.public_thread,
                    discord.ChannelType.private_thread,
                ]:
                    tc += 1
                elif channel.type in [
                    discord.ChannelType.voice,
                    discord.ChannelType.stage_voice,
                ]:
                    vc += 1

        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent()
        open_file = len(self.process.open_files())
        embed.add_field(
            name="Last Restart",
            value=f"{self.bot.startuptime()}\n**Last Update**\n{last_update}",
        )
        embed.add_field(
            name="Process",
            value=f"{memory_usage:.1f} MiB\n{cpu_usage:.1f}% of 1 CPU core"
            f"\n{open_file} open files",
        )
        embed.add_field(
            name="Stats",
            value=f"Commands since reboot: {sum(self.bot.stats['commands_counter'].values())}"
            f"\nMessages processed: {self.bot.stats['message_counter']}"
            f"\nUnique users: {len(self.bot.stats['users_counter'])}",
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.add_field(
            name="Service",
            value=f"In {guilds} servers\n{len(self.bot.cogs)} loaded modules",
        )
        embed.add_field(
            name="Members", value=f"{members} total\n{unique_members} unique"
        )
        embed.add_field(
            name="Channels", value=f"{total_c} total\n{tc} text\n{vc} voice"
        )
        embed.timestamp = utcnow()
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(About(bot))
