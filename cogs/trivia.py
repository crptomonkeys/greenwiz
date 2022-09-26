import asyncio
import random
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.cryptomonkey_util import print_orpiga, nifty
from utils.exceptions import InvalidInput
from utils.meta_cog import MetaCog
from utils.trivia_utils import rand_monkeymath


def check_trivia_resp(author, channel):
    def in_check(message):
        if message.author != author:
            return False
        if not hasattr(message, "channel") or not hasattr(message.channel, "id"):
            return False
        if message.channel.id != channel.id:
            return False
        try:
            message.reference
        except AttributeError:
            return False
        if (
            "correct" not in message.content.casefold()
            and "end trivia" not in message.content.casefold()
        ):
            return False
        return True

    return in_check


def check_author(author, channel):
    def in_check(message):
        if message.author != author:
            return False
        if not hasattr(message, "channel") or not hasattr(message.channel, "id"):
            return False
        if message.channel.id != channel.id:
            return False
        return True

    return in_check


async def wipe_routine(question):
    await asyncio.sleep(60 * 15)
    await question.edit(content="Question removed for longevity.")


class Trivia(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.ongoing_trivia = {}
        self.trivia_questions = {}
        asyncio.create_task(self.on_load())

    async def on_load(self):
        self.log("Waiting to fetch trivia questions from sheet...")
        if "googleapi" not in self.bot.cogs_initialized:
            self.bot.extensions_to_load -= 1
            self.log(
                "Trivia cog could not be loaded as its prerequisite cog Googleapi was not loaded.",
                "WARN",
            )
            return
        while not self.bot.cogs_ready.get("Googleapi", False):
            await asyncio.sleep(0.1)
        self.log("Fetching trivia questions from sheet...")
        sheet_vs = self.bot.sheet_values(
            self.bot.settings.SURVEY_2_SHEET_CODE,
            "'Validated Questions'!A2:B500",
        )
        self.log(f"Sheet_vs: {sheet_vs}", "DBUG")
        self.trivia_questions = {res[0]: res[1] for res in sheet_vs if len(res) >= 2}

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.max_concurrency(1, per=BucketType.guild)
    async def trivia(
        self,
        ctx,
        user: Optional[discord.User] = None,
        to: Optional[int] = 5,
        timeout: Optional[int] = 1800,
        *,
        topic: Optional[str] = None,
    ):
        """Start a trivia. Can specify who will run it (if not the person running the command), what the topic is,
        and how many points to go up to. All criteria are optional, but user *then* topic must be specified if topic
        is to be specified.
        While the trivia is ongoing, replying to a message with 'correct' will give that message's author a point.
        Points will be tallied and displayed either once one player reaches [to] points or after the event runner
        types 'end trivia'.
        Args:
            ctx: automatic
            user: The user who will run the trivia.
            to: The number of points to 'win' the trivia.
            timeout: The number of seconds to pass without a 'correct' from the trivia runner before assuming the
             trivia runner has abandoned the trivia. Default is 1800 seconds (30 minutes). Note that if you specify a
             custom timeout you must also specify a 'to' parameter.
            topic: The topic of this trivia. Default is 'Trivia Event'
        """
        initial_overwrites = ctx.channel.overwrites
        all_speak = initial_overwrites | {
            ctx.guild.default_role: discord.PermissionOverwrite(send_messages=True)
        }
        all_quiet = initial_overwrites | {
            ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)
        }
        self.ongoing_trivia[ctx.guild] = True

        user, topic = user or ctx.author, topic or "Trivia Event"
        await ctx.send(
            f"**{topic} has started in this channel.** Questions will be posted by {user.mention}, "
            f"and points will be awarded by them by replying to the first correct message with"
            f" 'correct'. Points will be automatically tallied and I'll let everyone know when"
            f" someone has reached {to} points or display the winners when {user.mention} types"
            f" 'end trivia'. {user.mention}, type the first question to begin."
        )
        while True:

            try:
                resp = await self.bot.wait_for(
                    "message", check=check_author(user, ctx.channel), timeout=timeout
                )
            except asyncio.TimeoutError:
                await ctx.send(
                    f"{timeout} seconds passed without hearing the next question from {user.mention}; I "
                    f"assume the event has come to an end."
                )
                break
            if "end trivia" in resp.content.casefold():
                break
            await ctx.channel.edit(overwrites=all_speak)
            try:
                resp = await self.bot.wait_for(
                    "message",
                    check=check_trivia_resp(user, ctx.channel),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                await ctx.send(
                    f"{timeout} seconds passed without hearing 'correct' from {user.mention}; I assume the "
                    f"event has come to an end."
                )
                break
            if not resp.reference:  # end trivia triggered
                break
            msg_id, channel_id = resp.reference.message_id, resp.reference.channel_id
            msg = await ctx.guild.get_channel(channel_id).fetch_message(msg_id)
            winner = msg.author
            new_points = await self.storage[ctx.guild].inc_trivia_points(winner, 1)
            if new_points >= to:
                await ctx.send(
                    f"{winner.mention} has reached {to} points! Congratulations! Ending trivia."
                )
                break
            await ctx.channel.edit(overwrites=all_quiet)
            await ctx.send(
                f"**The correct answer was:**\n`{msg.content[0:1000]}`\n{winner.mention} now has"
                f" {new_points} trivia points out of the {to} needed to win. "
                f"I've closed the channel. Ready for next question from {user.mention}."
            )
        res = await self.storage[ctx.guild].return_and_reset_trivia()
        sorted_res = sorted(res.items(), key=lambda x: x[1], reverse=True)
        result = {ctx.guild.get_member(id_): score for id_, score in sorted_res}
        to_send = f"**Results of {topic} by {user.mention}**\n"
        place = 1
        for member, score in result.items():
            line = f"**{place})** {member.mention} - {score} correct answers\n"
            place += 1
            if len(to_send) + len(line) < 2000:
                to_send += line
            else:
                await ctx.send(to_send)
                to_send = line
        await ctx.send(to_send)
        await ctx.channel.edit(overwrites=initial_overwrites)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def deduct(self, ctx: commands.Context, user: discord.User, amount=1):
        """Adjusts the amount of points user has in the ongoing trivia. Requires there to be an ongoing trivia. By
        default, deducts a single point from user's tally. You can optionally specify an amount after mentioning the
        user to deduct more points, or specify a negative amount to add points.
        Args:
            ctx: automatic
            user: The user whose points to adjust.
            amount: the number of points to give/take. Defaults to taking 1 point. To give points, use a negative
             number.
        """
        if not self.ongoing_trivia[ctx.guild]:
            return await ctx.send(
                "This command requires an ongoing trivia. Start one with the `trivia` command."
            )
        res = await self.storage[ctx.guild].inc_trivia_points(user, -1 * amount)
        await ctx.send(f"Okay, {user.mention} now has {res} points.")

    @commands.command()
    @commands.check(nifty())
    async def triviaq(self, ctx):
        """DMs the user a random question from the question bank."""
        await ctx.message.delete()
        self.log(self.trivia_questions, "DBUG")

        try:
            random_question1 = random.choice(list(self.trivia_questions))
        except IndexError:
            return await ctx.send(
                "Sorry, no trivia questions are currently loaded.", delete_after=10
            )
        answer = self.trivia_questions[random_question1]

        random_question2, answer2 = rand_monkeymath()

        random_question1.strip()
        if random_question1[-1] not in "?.":
            random_question1 += "?"
        random_question2.strip()
        if random_question2[-1] not in "?.":
            random_question2 += "?"

        question = await ctx.send(
            f"```md\n"
            f"You must answer BOTH questions in ONE message to get credit for this question."
            f"\n========"
            f"\n{random_question1}"
            f"\n========"
            f"\nMONKEYMATH: {random_question2}"
            f"\n========"
            f"\n```"
        )
        asyncio.create_task(wipe_routine(question))
        await ctx.author.send(
            f"The answer to `{random_question1}` is: `{answer}`\n\n"
            f"The answer to `{random_question2}` is: `{answer2}`"
        )

    @commands.command()
    @commands.check(print_orpiga())
    async def monkeymath(self, ctx: commands.Context, difficulty: int = 1):
        """Generates a novel monkeymath question with the given difficulty, posts it, and DMs the user the answer.
        Detects a correct answer if spelled correctly.
        Args:
            ctx: automatic
            difficulty (int): The question difficulty, from 1-5
        """
        if difficulty < 1 or difficulty > 5:
            raise InvalidInput("Difficulty must be between 1 and 5.")
        if difficulty > 1:
            raise NotImplementedError
        random_question, answer = rand_monkeymath()
        random_question.strip()
        if random_question[-1] not in "?.":
            random_question += "?"

        question = await ctx.send(
            f"```md\n"
            f"\n========"
            f"\nMONKEYMATH: {random_question}"
            f"\n========"
            f"\n```"
        )
        asyncio.create_task(wipe_routine(question))
        await ctx.author.send(f"The answer to `{random_question}` is: `{answer}`")
        # question, answer = generate_monkey_question(d=difficulty)
        # TODO Finish function


async def setup(bot):
    await bot.add_cog(Trivia(bot))
