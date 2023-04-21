import asyncio
from datetime import datetime
from difflib import get_close_matches
from typing import Union

import discord
from discord import Forbidden, HTTPException
from discord.ext import commands
from discord.ext.commands import Greedy
from tldextract import tldextract

from utils.exceptions import InvalidInput
from utils.meta_cog import MetaCog
from utils.settings import CM_GUID
from utils.util import scope
from utils.cryptomonkey_util import has_nifty


async def confirmation_on(user, confirmed_ids):
    await asyncio.sleep(20)
    confirmed_ids[user] = 0
    return


class Moderation(MetaCog):
    def __init__(self, bot):
        self.confirmed_ids = dict()
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.id not in [CM_GUID, 482266371632398339, 348929154114125827]:
            return
        if message.author.bot:
            return
        flag: Union[bool, str] = False
        banned_phrases = [
            "uni-airdrop.org",
            "uni-airdrop.io",
            "uni-claim.io",
            " https://marketplace-axieinfinity.com/claim.html",
            "https://1inch-airdrop.io/",
            "https://stake.com/?c=",
            "https://atomichub.ix.tc",
            "https://alienworlds.us",
            "https://steamcomminuty.com",
            "https://dlscorld.gift",
            "invest and earn $",
            "if interested send me a direct message via whatsapp by",
            "(225) 377‑0714",
            "https://discord.gg/wnXzAMzNG7",
        ]

        riskful_hostnames = ["atomichub.io", "neftyblocks.com", "cryptomonkeys.cc"]

        content = message.content.lower().replace(" ", "")
        for phrase in banned_phrases:
            if phrase in content:
                self.bot.log(f"Scam detection: {message.content}", "NOTI")
                flag = "posting scam website links"

        tokens = content.split(" ")
        for token in tokens:
            if "?key=" in token or "http://" in token or "https://" in token:
                url = tldextract.extract(token)
                host = f"{url.domain}.{url.suffix}"
                nears = get_close_matches(host, riskful_hostnames, cutoff=0.78)
                identicals = get_close_matches(host, riskful_hostnames, cutoff=1)
                if len(nears) > len(identicals):
                    flag = "posting scam claim links"
                    break

        if not flag and "uniswap" in content and "second" in content:
            banned_modifiers = ["cool", "legit", "nice", "makes", "airdrop"]
            for phrase in banned_modifiers:
                if phrase in content:
                    flag = "posting scam website links"
                    break

        if (
            not flag
            and "atomichub." in content
            and "?key=" in content
            and "atomichub.io" not in content
        ):
            flag = "posting scam claim links"
        if (
            not flag
            and "neftyblocks." in content
            and "?key=" in content
            and "neftyblocks.com" not in content
        ):
            flag = "posting scam website links"

        if not flag and len(message.mentions) > 20 and not has_nifty(message.author):
            flag = "mass pinging people"

        if not flag:
            return

        self.bot.log(
            f"Likely scam/spam detection: {message.content}, flag: {flag}", "NOTI"
        )
        channel = message.guild.get_channel(770556844351422464) or message.channel

        if flag == "posting scam claim links":
            contents = content[:1940].replace("`", "")
            await channel.send(
                f"<@&733313838375632979>, I think I detected {message.author} "
                f"({message.author.mention}) {flag}. Please take a look and ban"
                f" them if this is malicious.\n{message.jump_url}\n"
                f"Message content (don't click):\n```\n{contents}\n```"
            )
            return

        try:
            await message.author.ban(reason=f"Automatic ban for {flag}")
            await channel.send(
                f"<@&733313838375632979>, I'm automatically banning {message.author}"
                f" ({message.author.id}) for {flag} in channel {message.channel}."
            )
            if channel != message.channel:
                contents = content[:1940].replace("`", "")
                await channel.send(
                    f"Contents of the offending message:\n```\n{contents}\n```"
                )
            self.bot.log(f"Banned {message.author} ({message.author.id})")
        except discord.Forbidden:
            await channel.send(
                f"I tried to ban {message.author} ({message.author.id}) but do not have permissions to"
                f" do so."
            )
        except discord.HTTPException:
            await channel.send(
                f"I tried to ban {message.author} ({message.author.id}) but something went wrong on "
                f"discord's end."
            )

    # Commands
    @commands.command(
        aliases=["clear", "del", "purge"], description="Delete a number of messages"
    )
    @commands.check(scope())
    @commands.has_permissions(manage_messages=True)
    async def purge_msgs(self, ctx: commands.Context, amount):
        """Delete a bunch of messages
        Requires: Manage Message perms on your server
        Amount: The number of messages to purge. Typically limited to 100."""
        if int(amount) <= 100:
            await ctx.channel.purge(limit=int(amount) + 1)
            self.bot.log(
                f"{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.",
                self.bot.cmd,
            )
        else:
            await ctx.send("You may only delete up to 100 messages", delete_after=20)

    @commands.command(name="forcepurge", description="Delete a number of messages")
    @commands.is_owner()
    async def forcepurge(self, ctx: commands.Context, amount):
        """Delete a bunch of messages
        This is meant for use only in cases where the bot has caused spam that it shouldn't have.
        Amount: The number of messages to purge."""
        await ctx.channel.purge(limit=int(amount) + 1)
        self.bot.log(
            f"{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.",
            self.bot.cmd,
        )

    @commands.command(name="kick", description="Kick em out!")
    @commands.check(scope())
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason="No reason provided.",
    ):
        """Kick someone out of the server
        Requires: Kick Members permission
        Member: the person to kick
        Reason: the reason why, defaults to 'No reason provided.'"""
        reason = f"{ctx.author} kicked {member} for reason {reason}"
        await member.kick(reason=reason)
        self.bot.log(f"{ctx.author} kicked {member} from {ctx.guild} for {reason}.")

    @commands.command(name="ban", description="The Banhammer!")
    @commands.check(scope())
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason="No reason provided.",
    ):
        """Ban someone from the server
        Requires: Ban Members permission
        Member: the person to ban
        Reason: the reason why, defaults to 'No reason provided.'"""
        reason = f"{ctx.author} banned {member} for reason {reason}"
        await member.ban(reason=reason)
        await ctx.send(f"Banned {member.mention} for {reason}.")
        self.bot.log(
            f"{ctx.author} banned {member} from {ctx.guild} for {reason}.",
            self.bot.prio,
        )

    @commands.command(description="Unban a member")
    @commands.check(scope())
    @commands.has_permissions(manage_guild=True)
    async def unban(self, ctx: commands.Context, *, member: discord.Member):
        """Unban someone from the server
        Requires: Manage Server permission
        Member: the person to unban"""
        await ctx.guild.unban(member)
        await ctx.send(f"Unbanned {member} ({member.id})")
        self.bot.log(f"{ctx.author} unbanned {member} from {ctx.guild}.", self.bot.cmd)

    @commands.command(
        name="clearpins", description="Remove *all* the pins from a channel"
    )
    @commands.check(scope())
    @commands.has_permissions(manage_messages=True)
    async def clearpins(self, ctx):
        """Clear all the pinned messages from a channel.
        Requires: Manage Messages permission
        Note: It is highly recommended to be absolutely sure before using this command.
        """
        if self.confirmed_ids.get(ctx.author.id, 0) > 0:
            i = 0
            for pin in await ctx.channel.pins():
                await pin.unpin()
                i += 1
            await ctx.send(f"Okay {ctx.author}, {i} pins have been cleared.")
            self.confirmed_ids[ctx.author.id] = 0
            await ctx.message.delete()  # delete the command
        else:
            await ctx.send(
                "Are you certain you wish to clear all the pins from this channel? This can not be undone. "
                "If so, use this command again.",
                delete_after=20,
            )
            self.confirmed_ids[ctx.author.id] = 1
            await ctx.message.delete()  # delete the command
            asyncio.create_task(confirmation_on(ctx.author.id, self.confirmed_ids))
        self.bot.log(
            f"Clearpins command used by {ctx.author} in channel {ctx.channel.name}.",
            self.bot.cmd,
        )

    @commands.command(name="massban", description="Ban a list of user ids.")
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx: commands.Context, users: Greedy[discord.User]):
        """Mass bans a list of discord IDs. Please use this wisely. This command will NOT delete messages."""
        banned_list = []
        failed_to_ban = []
        for user in users:
            try:
                await ctx.guild.ban(
                    user,
                    reason=f"Mass banned through massban command by {ctx.author}.",
                    delete_message_days=0,
                )
                banned_list.append((user.name, user.id))
            except (Forbidden, HTTPException):
                failed_to_ban.append(user)
        self.bot.recently_massbanned = banned_list

        if len(failed_to_ban) > 0:
            to_send = f"Failed to ban: {[user.name for user in failed_to_ban]}"[:1990]
            await ctx.send(to_send)
        return await ctx.send(
            f"Successfully banned {len(banned_list)} users by {ctx.author}'s request."
        )

    @commands.command(
        name="banlast10m",
        description="Ban everyone who joined the server in the last 10 minutes.",
    )
    @commands.has_permissions(ban_members=True)
    async def banlast10m(
        self, ctx: commands.Context, minutes: int = 10, *, age_in_months=6
    ):
        """Mass bans everyone who joined the server in the last 10 minutes."""
        if minutes > 60 or minutes < 2:
            raise InvalidInput("Must be between 2 and 60 minutes.")
        ten_ago = datetime.now().timestamp() - 60 * minutes
        n_months_ago = datetime.now().timestamp() - 60 * 60 * 24 * 30 * age_in_months
        banned_list = []
        failed_to_ban = []
        for user in ctx.guild.members:
            if (
                user.joined_at.timestamp() > ten_ago
                and user.created_at.timestamp() > n_months_ago
            ):
                try:
                    await ctx.guild.ban(
                        user,
                        reason=f"Mass banned through banlast10m command by {ctx.author}",
                    )
                    banned_list.append((user.name, user.id))
                except (Forbidden, HTTPException):
                    failed_to_ban.append(f"{user} (unable)")
            elif user.created_at.timestamp() > n_months_ago:
                failed_to_ban.append(f"{user} (account >{age_in_months}m old)")
        self.bot.recently_massbanned = banned_list

        account_age_warning = """If you would like to ban older accounts, you can
         format your command like `banlast10m 10 12 to ban all accounts younger
         than 12 months old that joined in the last 10 minutes. Please use
         extreme caution when setting an account age.`"""

        if len(failed_to_ban) > 0:
            to_send = f'Failed to ban: {",".join([res for res in failed_to_ban])}'[
                :1990
            ]
            await ctx.send(to_send)
            await ctx.send(account_age_warning)
        return await ctx.send(
            f"Successfully banned {len(banned_list)} users with account ages less than {age_in_months} months by"
            f" {ctx.author}'s request."
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
