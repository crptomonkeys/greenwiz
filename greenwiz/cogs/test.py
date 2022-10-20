from typing import Optional, Union

import discord
from discord.ext import commands

from utils.cryptomonkey_util import nifty
from utils.util import utcnow, load_words
from utils.exceptions import InvalidInput
from utils.meta_cog import MetaCog
from utils.util import scope
from wax_chain.wax_util import get_card_dict


def check(author):
    def in_check(message):
        return message.author == author

    return in_check


def check_opts(author):
    def in_check(message):
        global opts
        return message.author == author and message.content in opts

    return in_check


class Test(MetaCog):
    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        await get_card_dict(self.session)
        self.bot.word_list = load_words()
        self.bot.word_list += [word.upper() for word in self.bot.word_list]
        await super().on_ready()

    # Commands
    @commands.command(hidden=True)
    @commands.check(scope())
    async def test(self, ctx):
        await ctx.send("test")
        self.bot.log(f"Test command used by {ctx.author} at {utcnow()}.", self.bot.cmd)

    @commands.command(
        description="Tests command parsing for a future iteration of ,drop."
    )
    @commands.guild_only()
    async def testdrop(
        self,
        ctx,
        member: Union[discord.Member, str],
        num: Optional[int] = 1,
        *,
        reason: str = "No reason",
    ):
        """
        **Test command, doesn't actually send anything.**
        Sends the target member a random cryptomonkey claim link from the cryptomonkeys account.
        Target may be a discord member (will DM a claimlink) or a wax address (will directly transfer assets).
        If there aren't any stored, tells you so.
        You can specify a reason after the name.
        MonkeyPrinters may optionally specify a number of cards to send, before the reason but after the
        name. Defaults to 1. (Others can also specify a number, but it will always be overwritten by 1)
        """
        if not 1 <= num <= 10:
            raise InvalidInput("Num must be between 1 and 10.")

        if type(member) == discord.Member:
            return await ctx.send(
                f"Interpreted test command as: Send {num} random cryptomonKeys to discord user"
                f" {member} asa DMed claimlink for reason {reason}."
            )
        if len(member) > 12:
            raise InvalidInput("Member must be either a discord user or a wax address.")

        if ".wam" in member:
            return await ctx.send(
                f"Interpreted test command as: Send {num} random cryptomonKeys by direct transfer to "
                f"cloud wallet address {member} for reason {reason}."
            )
        elif len(member) == 12:
            return await ctx.send(
                f"Interpreted test command as: Send {num} random cryptomonKeys by direct transfer to "
                f"custom wallet address {member} for reason {reason}."
            )
        elif member in self.bot.special_addr_list:
            return await ctx.send(
                f"Interpreted test command as: Send {num} random cryptomonKeys by direct transfer "
                f"to valid top level wallet address {member} for reason {reason}."
            )
        elif "." in member and member.split(".")[1] in self.bot.special_addr_list:
            return await ctx.send(
                f"Interpreted test command as: Send {num} random cryptomonKeys by direct transfer "
                f'to valid subdomain wallet address {member} (subdomain of {member.split(".")[1]}) '
                f"for reason {reason}."
            )
        await ctx.send(
            "Failed to interpret member. It is a string of the correct length to be a"
            " valid wax address in theory but isn't actually a valid wax address."
        )

    @commands.command(description="Finds words in a random key.")
    @commands.check(nifty())
    @commands.check(scope())
    async def find_words(
        self, ctx: commands.Context, min_length: Optional[int] = 4, *, text
    ):

        test_strings = text.split()
        words = self.bot.word_list
        for test_string in test_strings:
            for word in words:
                if len(word) < min_length:
                    continue
                cursor = 0
                candidate = test_string
                for i in word:
                    cursor = test_string.find(i, cursor) + 1
                    candidate = f"{candidate[:cursor - 1]}_{candidate[cursor:]}"
                    if cursor < 1:
                        break
                else:
                    await ctx.send(
                        f"Found `{word}` in `{test_string}`    : `{candidate}`"
                    )
        await ctx.send("Finished search.")


async def setup(bot):
    await bot.add_cog(Test(bot))
