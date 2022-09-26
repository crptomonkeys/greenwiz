import asyncio
import datetime

import discord
import pytz
from discord.ext import commands

import utils.settings
from utils.meta_cog import MetaCog
from utils.util import log, scope, now_stamp


async def remind_routine(increments, user, author, message):
    if user is author:
        message = ":alarm_clock: **Reminder:** \n" + message
    else:
        message = f":alarm_clock: **Reminder from {author}**: \n" + message
    await asyncio.sleep(increments)
    await user.send(message)
    log(f"{user} has been sent their reminder {message}")


class Basics(MetaCog):

    # ==============================Reaction handler======================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        bot_id = self.bot.user.id
        if payload.user_id == bot_id:
            return

        if str(payload.emoji) == "<:tick:773298413898039297>":
            channel = self.bot.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            if msg.author.id != bot_id:
                return
            if len(msg.embeds) > 0:
                embed = msg.embeds[0]
                old_title = embed.title
                old_txt = embed.description
                embed.title = f"~~{old_title}~~"
                embed.description = f"~~{old_txt}~~"
                try:
                    await msg.edit(embed=embed)
                except discord.errors.Forbidden:
                    self.bot.log(
                        f"Hmm, I tried to edit a message but something went wrong. Author: {msg.author}, "
                        f"Content: {msg.content}",
                        "WARN",
                    )

    # Commands
    @commands.command(name="ping", aliases=["plonk"], description="Pong!")
    @commands.check(scope())
    async def ping(self, ctx):
        """Returns the ping to the bot"""
        ping = round(self.bot.latency * 1000)
        await ctx.message.delete(delay=20)  # delete the command
        await ctx.send(f"Ping is {ping}ms.", delete_after=20)
        self.bot.log(
            f"Ping command used by {ctx.author} at {now_stamp()} with ping {ping}",
            self.bot.cmd,
        )

    # Send you a reminder DM with a custom message in a custom amount of time
    @commands.command(
        name="remind",
        aliases=["rem", "re", "r", "remindme", "tellme", "timer"],
        description="Send reminders!",
    )
    @commands.check(scope())
    async def remind(self, ctx: commands.Context, *, reminder=None):
        """Reminds you what you tell it to.
        Example: ,remind take out the trash in 10m
        Your reminder needs to end with in and then the amount of time you want to be reminded in.
        10s: 10 seconds from now
        10m: 10 minutes from now
        1h:   1 hour from now
        1d: tomorrow at this time
        1w: next week at this time
        1y: next year (or probably never, as the bot currently forgets reminders if it restarts)"""
        try:
            self.bot.log(ctx.message.raw_mentions[0], "DBUG")
            user = ctx.guild.get_member(ctx.message.raw_mentions[0])
        except (IndexError, AttributeError):
            user = None
        if user is None:
            user = ctx.author
        try:
            t = reminder.rsplit(" in ", 1)
            reminder = t[0]
            increments = 0
            t_ = t[1][:-1]
        except (IndexError, AttributeError):
            return await ctx.send_help("remind")
        if (
            t_.isdecimal()
        ):  # true if in 15m format is proper, 1 letter at the end preceded by a number
            # preceded by in
            increments = int(t[1][:-1])  # number of increment to wait
            increment = t[1][-1]  # s, m, h, d, w, y
            time_options = {
                "s": 1,
                "m": 60,
                "h": 60 * 60,
                "d": 60 * 60 * 24,
                "w": 60 * 60 * 24 * 7,
                "y": 60 * 60 * 24 * 365,
            }
            increments *= time_options.get(increment, 1)
            self.bot.log(
                f"{ctx.author} created a reminder to {user} for {increments} seconds from now; {t}",
                self.bot.cmd,
            )
            asyncio.create_task(remind_routine(increments, user, ctx.author, reminder))
            await ctx.send(
                f"Got it. I'll send the reminder in {increments} seconds.",
                delete_after=20,
            )
        else:
            await ctx.send(
                "Please enter a valid time interval. You can use s, m, h, d, w, y as your interval time "
                "prefix.",
                delete_after=20,
            )
        await ctx.message.delete(delay=20)  # delete the command
        self.bot.log(
            f"Remind command used by {ctx.author} at {now_stamp()} with reminder {reminder} to user {user} "
            f"for time {increments}.",
            self.bot.cmd,
        )

    # Send you a reminder DM with a custom message in a custom amount of time
    @commands.command(
        aliases=["do", "tod", "tdo", "to", "+", "="], description="Add a todo message"
    )
    @commands.guild_only()
    @commands.check(scope())
    async def todo(self, ctx: commands.Context, *, reminder=None):
        """
        Adds a to do message to your to do list in that channel
        """
        if not reminder:
            return ctx.send_help("todo")
        t = reminder.rsplit(" by ", 1)
        if len(t) < 2:
            t = reminder.rsplit(" in ", 1)
            if len(t) < 2:
                # No time specified
                t += ["10d"]

        reminder = t[0]
        if t[1][
            :-1
        ].isdecimal():  # true if in 15m format is proper, 1 letter at the end preceded by a number
            # preceded by in
            increments = int(t[1][:-1])  # number of increment to wait
            increment = t[1][-1]  # s, m, h, d, w, y
        else:
            increments = 1
            increment = "w"
        time_options = {
            "s": 1,
            "m": 60,
            "h": 60 * 60,
            "d": 60 * 60 * 24,
            "w": 60 * 60 * 24 * 7,
            "y": 60 * 60 * 24 * 365,
        }
        increments *= time_options.get(increment, 1)
        due = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=increments)
        self.bot.log(
            f"{ctx.author} created a todo message to {reminder} for {increments} seconds from now; {t}",
            self.bot.cmd,
        )
        previous_num = 0
        async for message in ctx.channel.history(limit=5):
            if message.author == ctx.guild.me and len(message.embeds) > 0:
                num_str = message.embeds[0].title.replace("~", "").split("#")[-1]
                try:
                    previous_num = int(num_str)
                except ValueError:
                    return await ctx.send(
                        "Couldn't extract number from the previous todo in this channel."
                    )
                break
        embed = discord.Embed(title=f"#{previous_num + 1}", description=reminder)
        embed.set_footer(text="Due")
        embed.timestamp = due
        resp = await ctx.send(embed=embed)
        await resp.add_reaction("<:tick:773298413898039297>")
        await ctx.message.delete(delay=3)  # delete the command
        self.bot.log(
            f"Todo command used by {ctx.author} at {now_stamp()} with reminder {reminder}.",
            self.bot.cmd,
        )


async def setup(bot):
    await bot.add_cog(Basics(bot))
