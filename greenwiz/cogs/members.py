import discord
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.settings import BASIC_PERMS, SIGNIFICANT_PERMS
from utils.util import scope, embed_footer, now_stamp


class Members(MetaCog):
    @commands.Cog.listener()
    @commands.guild_only()
    async def on_member_join(self, member: discord.Member):
        self.bot.log(f"{member.display_name} has joined {member.guild}.", "DBUG")

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_member_remove(self, member: discord.Member):
        self.bot.log(f"{member.display_name} has left {member.guild}.", "DBUG")

    # List out the perms of a member
    @commands.command(
        name="perms",
        aliases=["permissions", "checkperms", "whois", "perm"],
        description="Who dat?",
    )
    @commands.check(scope())
    @commands.guild_only()
    async def check_permissions(
        self, ctx: commands.Context, member: discord.Member = None, detail=1
    ):
        """Check the permissions of a user on the current server
        Member: The person who's perms to check
        Detail: 1 for significant perms, 2 for notable perms, 3 for all perms"""
        # assign caller of command if no one is chosen
        if not member:
            member = ctx.author
        if not isinstance(member, discord.Member):
            raise AssertionError("member should be a discord.Member object.")
        # embed it
        embed = discord.Embed(title="", description="", color=member.color)
        embed.set_author(
            icon_url=member.display_avatar.url,
            name=f"{str(member)}'s perms on {ctx.guild.name}",
        )
        if detail > 0:  # include basic perms
            iperms = "\n".join(
                perm
                for perm, value in member.guild_permissions
                if str(perm) in BASIC_PERMS
                if value
            )
            if len(iperms) < 1:
                iperms += "None"
            embed.add_field(name="Important Perms:", value=iperms)
        else:
            embed.add_field(name="There was an error.", value="Error")
        if detail > 1:  # include notable perms
            nperms = "\n".join(
                perm
                for perm, value in member.guild_permissions
                if str(perm) in SIGNIFICANT_PERMS
                if value
            )
            if len(nperms) < 1:
                nperms += "None"
            embed.add_field(name="Notable Perms:", value=nperms)
        if detail > 2:
            # include the rest of the perms
            perms = "\n".join(
                perm
                for perm, value in member.guild_permissions
                if str(perm) not in (BASIC_PERMS + SIGNIFICANT_PERMS)
                if value
            )
            if len(perms) < 1:
                perms += "None"
            embed.add_field(name="Other Perms:", value=perms)
        embed.set_footer(text=embed_footer(ctx.author))
        await ctx.send(content=None, embed=embed)
        self.bot.log(
            f"Perms command used by {ctx.author} at {now_stamp()} on member {member} with detail {detail}.",
            self.bot.cmd,
        )


async def setup(bot):
    await bot.add_cog(Members(bot))
